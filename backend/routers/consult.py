"""个案咨询 API：画像抽取、问答生成。"""

import json
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend import db
from backend.chroma_store import search_literature
from backend.config import settings
from backend.ingest.extract import ExtractError, extract_document
from backend.llm.completion import get_chat_client
from backend.llm.embedding import get_embedding_client
from backend.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from backend.retrieval.safety import DISCLAIMER, check_high_risk, refused_response
from backend.retrieval.web_search import search_web

router = APIRouter(prefix="/api", tags=["consult"])

MODEL_MAP = {
    "DeepSeek-V3": "deepseek-chat",
    "deepseek-chat": "deepseek-chat",
    "deepseek-v3": "deepseek-chat",
}


class ProfileData(BaseModel):
    sourceName: str = ""
    age: str = ""
    coreSymptoms: list[str] = Field(default_factory=list)
    assessments: list[str] = Field(default_factory=list)
    note: str = ""


class AskConfig(BaseModel):
    model: str = "deepseek-chat"
    topK: int = 4
    enableWebSearch: bool = False


class AskRequest(BaseModel):
    question: str
    profile: ProfileData | None = None
    config: AskConfig = Field(default_factory=AskConfig)


def _resolve_model(name: str) -> str:
    return MODEL_MAP.get(name, settings.llm_model)


def _profile_text(profile: ProfileData | None) -> str:
    if not profile:
        return ""
    parts = []
    if profile.age:
        parts.append(f"年龄：{profile.age}")
    if profile.coreSymptoms:
        parts.append(f"核心表现：{'、'.join(profile.coreSymptoms)}")
    if profile.assessments:
        parts.append(f"既往评估：{'、'.join(profile.assessments)}")
    return "；".join(parts)


def _build_retrieval_query(question: str, profile: ProfileData | None) -> str:
    profile_part = _profile_text(profile)
    if profile_part:
        return f"{question}\n个案：{profile_part}"
    return question


def _format_citations(chunks: list[dict]) -> list[dict]:
    return [
        {
            "id": i,
            "source": c["source"],
            "loc": c["loc"],
            "snippet": c["snippet"],
        }
        for i, c in enumerate(chunks, start=1)
    ]


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 返回非合法 JSON: {exc}") from exc


def _format_web_citations(web_hits: list[dict]) -> list[dict]:
    return [
        {
            "id": w["id"],
            "title": w.get("title") or "未知标题",
            "url": w.get("url") or "",
            "snippet": w.get("snippet") or "",
        }
        for w in web_hits
    ]


def _coerce_web_refs(refs: Any, web_hits: list[dict]) -> list[str]:
    valid_ids = {w["id"] for w in web_hits}
    id_by_num = {i: f"W{i}" for i in range(1, len(web_hits) + 1)}
    out: list[str] = []
    for r in refs or []:
        if isinstance(r, str):
            token = r.strip().upper()
            if token in valid_ids:
                out.append(token)
                continue
            m = re.search(r"\d+", r)
            if m:
                wid = id_by_num.get(int(m.group()))
                if wid and wid in valid_ids:
                    out.append(wid)
        elif isinstance(r, int):
            wid = id_by_num.get(r)
            if wid and wid in valid_ids:
                out.append(wid)
    return out


def _coerce_refs(refs: Any, chunk_count: int) -> list[int]:
    out: list[int] = []
    for r in refs or []:
        if isinstance(r, int) and 1 <= r <= chunk_count:
            out.append(r)
        elif isinstance(r, float) and 1 <= int(r) <= chunk_count:
            out.append(int(r))
        elif isinstance(r, str):
            m = re.search(r"\d+", r)
            if m:
                n = int(m.group())
                if 1 <= n <= chunk_count:
                    out.append(n)
    return out


def _insufficient_response(profile_text: str, *, reason: str) -> dict[str, Any]:
    return {
        "refused": False,
        "insufficientLiterature": True,
        "profileEcho": profile_text,
        "suggestions": [
            {
                "text": reason,
                "refs": [],
            }
        ],
        "cautions": [
            "请上传与孤独症（ASD）早期干预相关的权威文献，如诊疗指南、循证综述、家庭训练手册等。",
            "知识库中的无关文档（如合同、通知）会影响检索质量，建议在文献库中删除。",
        ],
        "whenToSeeDoctor": ["若孩子有发育或行为方面的疑虑，请尽快到具备资质的专业机构评估。"],
        "citations": [],
        "webCitations": [],
        "disclaimer": DISCLAIMER,
    }


def _normalize_answer(
    parsed: dict[str, Any],
    chunks: list[dict],
    profile_text: str,
    *,
    web_hits: list[dict] | None = None,
    literature_missing: bool = False,
) -> dict[str, Any]:
    web_hits = web_hits or []
    suggestions = parsed.get("suggestions") or parsed.get("suggestion") or []
    if isinstance(suggestions, dict):
        suggestions = [suggestions]
    if isinstance(suggestions, str):
        suggestions = [{"text": suggestions, "refs": []}]

    normalized_suggestions = []
    for item in suggestions:
        if isinstance(item, str):
            item = {"text": item, "refs": []}
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("content") or item.get("suggestion") or "").strip()
        refs = _coerce_refs(item.get("refs") or item.get("references") or [], len(chunks))
        web_refs = _coerce_web_refs(item.get("webRefs") or item.get("web_refs") or [], web_hits)
        if not text:
            continue
        normalized_suggestions.append({"text": text, "refs": refs, "webRefs": web_refs})

    if not normalized_suggestions:
        if web_hits:
            fallback = "未命中本地权威文献，以下为基于网络检索的方向性补充，请结合专业评估使用。"
            return {
                "refused": False,
                "literatureMissing": True,
                "profileEcho": profile_text,
                "suggestions": [{"text": fallback, "refs": [], "webRefs": []}],
                "cautions": [
                    "未命中本地权威文献，网络内容仅供参考，不构成医疗诊断或治疗方案。",
                ],
                "whenToSeeDoctor": ["若孩子有发育或行为方面的疑虑，请尽快到专业机构评估。"],
                "citations": [],
                "webCitations": _format_web_citations(web_hits),
                "disclaimer": DISCLAIMER,
            }
        cautions = [str(c) for c in (parsed.get("cautions") or []) if str(c).strip()]
        fallback = (
            cautions[0]
            if cautions
            else "现有文献不足以回答您的问题。请先在「文献知识库」上传相关权威文献后再提问。"
        )
        return _insufficient_response(profile_text, reason=fallback)

    result: dict[str, Any] = {
        "refused": False,
        "profileEcho": profile_text,
        "suggestions": normalized_suggestions,
        "cautions": [str(c) for c in (parsed.get("cautions") or []) if str(c).strip()] or [
            "干预需循序渐进，关注孩子情绪与配合度。"
        ],
        "whenToSeeDoctor": [
            str(c) for c in (parsed.get("whenToSeeDoctor") or []) if str(c).strip()
        ] or ["若伴随明显发育倒退或严重行为问题，应尽快就医。"],
        "citations": _format_citations(chunks),
        "webCitations": _format_web_citations(web_hits),
        "disclaimer": str(parsed.get("disclaimer") or DISCLAIMER),
    }
    if literature_missing:
        result["literatureMissing"] = True
        if not any("未命中" in c or "本地" in c for c in result["cautions"]):
            result["cautions"].insert(
                0,
                "未命中本地权威文献，网络内容仅作补充参考，请优先上传并依赖权威文献。",
            )
    return result


@router.post("/case/profile")
async def extract_profile(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {file.filename}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    tmp = Path(tempfile.mkdtemp(prefix="asd_case_")) / (file.filename or "report")
    try:
        tmp.write_bytes(content)
        segments = extract_document(tmp)
        char_count = sum(len(s["text"]) for s in segments)
        if char_count < 20:
            raise HTTPException(status_code=400, detail="报告内容过短，无法抽取有效文本")

        return {
            "sourceName": file.filename or tmp.name,
            "age": "",
            "coreSymptoms": [],
            "assessments": [],
            "note": f"已从报告中抽取约 {char_count} 字文本，请根据孩子真实情况填写年龄、核心表现与既往评估后再提问。",
        }
    except ExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()


@router.post("/case/ask")
def ask_case(body: AskRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    risk = check_high_risk(question)
    if risk:
        result = refused_response(risk)
        db.insert_qa_log(
            session_id=str(uuid.uuid4()),
            question=question,
            profile=body.profile.model_dump() if body.profile else None,
            retrieved=[],
            answer=result,
            model=body.config.model,
            top_k=body.config.topK,
        )
        return result

    top_k = max(1, min(body.config.topK, 10))
    profile_text = _profile_text(body.profile)
    query = _build_retrieval_query(question, body.profile)

    embed_client = get_embedding_client()
    query_vec = embed_client.embed([query])[0]
    chunks = search_literature(query_embedding=query_vec, top_k=top_k)

    web_hits: list[dict] = []
    if body.config.enableWebSearch:
        web_hits = search_web(query, max_results=settings.web_search_max_results)

    if not chunks and not web_hits:
        result = _insufficient_response(
            profile_text,
            reason=(
                "未在知识库中检索到与您问题相关的文献片段。"
                "请先在「文献知识库」上传孤独症早期干预相关的权威文献（指南、综述等），"
                "或勾选「网络补充检索」获取方向性参考。"
            ),
        )
        db.insert_qa_log(
            session_id=str(uuid.uuid4()),
            question=question,
            profile=body.profile.model_dump() if body.profile else None,
            retrieved=[],
            answer=result,
            model=body.config.model,
            top_k=top_k,
        )
        return result

    literature_missing = not chunks and bool(web_hits)
    user_prompt = build_user_prompt(
        question=question,
        profile_text=profile_text,
        chunks=chunks,
        web_hits=web_hits,
    )

    try:
        chat_client = get_chat_client()
        raw = chat_client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=_resolve_model(body.config.model),
            response_format={"type": "json_object"},
        )
        parsed = _parse_llm_json(raw)
        result = _normalize_answer(
            parsed,
            chunks,
            profile_text,
            web_hits=web_hits,
            literature_missing=literature_missing,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {exc}") from exc

    retrieved_log = [
        {"type": "literature", **c} for c in chunks
    ] + [{"type": "web", **w} for w in web_hits]

    db.insert_qa_log(
        session_id=str(uuid.uuid4()),
        question=question,
        profile=body.profile.model_dump() if body.profile else None,
        retrieved=retrieved_log,
        answer=result,
        model=body.config.model,
        top_k=top_k,
    )
    return result
