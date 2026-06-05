"""文献知识库 API。"""

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend import db
from backend.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, TAGS
from backend.ingest.pipeline import ingest_files_iter, remove_document

router = APIRouter(prefix="/api", tags=["literature"])


def _cleanup_tmp(tmp_dir: Path, saved: list[tuple[str, Path]]) -> None:
    for _, p in saved:
        p.unlink(missing_ok=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/documents")
def list_documents():
    return db.list_documents()


@router.get("/stats")
def get_stats():
    return db.get_stats()


@router.get("/tags")
def get_tags():
    return {"tags": TAGS}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    if not remove_document(doc_id):
        raise HTTPException(status_code=404, detail="文献不存在")
    return {"ok": True}


@router.post("/documents/ingest")
async def ingest_documents(
    files: list[UploadFile] = File(...),
    tag: str = Form("综合指南"),
    chunk_size: int = Form(DEFAULT_CHUNK_SIZE),
    overlap: int = Form(DEFAULT_CHUNK_OVERLAP),
):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    allowed = {".pdf", ".doc", ".docx", ".txt"}
    saved: list[tuple[str, Path]] = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="asd_ingest_"))

    try:
        for uf in files:
            suffix = Path(uf.filename or "").suffix.lower()
            if suffix not in allowed:
                raise HTTPException(status_code=400, detail=f"不支持的格式: {uf.filename}")
            dest = tmp_dir / (uf.filename or "upload")
            content = await uf.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"文件为空: {uf.filename}")
            dest.write_bytes(content)
            saved.append((uf.filename or dest.name, dest))

        def event_stream():
            try:
                for event in ingest_files_iter(
                    saved,
                    tag=tag,
                    chunk_size=chunk_size,
                    overlap=overlap,
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                _cleanup_tmp(tmp_dir, saved)

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except HTTPException:
        _cleanup_tmp(tmp_dir, saved)
        raise
    except Exception:
        _cleanup_tmp(tmp_dir, saved)
        raise
