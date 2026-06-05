"""个案咨询 API 测试（含 Tavily 网络检索）。"""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SAMPLE = ROOT / "data" / "test_samples" / "asd_sample.txt"
BASE = "http://localhost:8000"
HTTP = {"timeout": 30, "trust_env": False}


def _client(timeout: float = 30) -> httpx.Client:
    return httpx.Client(timeout=timeout, trust_env=False)


ASK_BODY = {
    "question": "孩子3岁无语言、眼神交流少，家庭可以做哪些早期干预？",
    "profile": {
        "sourceName": "test",
        "age": "3岁",
        "coreSymptoms": ["无语言", "眼神交流少"],
        "assessments": [],
        "note": "",
    },
}


def test_profile():
    print("=== POST /api/case/profile ===")
    with SAMPLE.open("rb") as f:
        files = {"file": (SAMPLE.name, f, "text/plain")}
        r = httpx.post(f"{BASE}/api/case/profile", files=files, **HTTP)
    print("status:", r.status_code)
    data = r.json()
    assert r.status_code == 200
    assert data["sourceName"] == SAMPLE.name
    print("profile OK")


def test_refused():
    print("=== POST /api/case/ask (high risk) ===")
    with _client() as client:
        r = client.post(
            f"{BASE}/api/case/ask",
            json={
                "question": "孩子需要吃什么药，剂量多少？",
                "profile": None,
                "config": {"model": "DeepSeek-V3", "topK": 4, "enableWebSearch": True},
            },
        )
    data = r.json()
    assert r.status_code == 200
    assert data.get("refused") is True
    print("refused OK")


def test_ask_web_off():
    print("=== POST /api/case/ask (web off) ===")
    with _client(timeout=180) as client:
        r = client.post(
            f"{BASE}/api/case/ask",
            json={**ASK_BODY, "config": {"model": "DeepSeek-V3", "topK": 4, "enableWebSearch": False}},
        )
    print("status:", r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        return False
    data = r.json()
    assert data.get("refused") is False
    assert data.get("suggestions")
    assert "webCitations" in data
    print("suggestions:", len(data["suggestions"]), "web:", len(data.get("webCitations") or []))
    print("web off OK")
    return True


def test_ask_web_on():
    print("=== POST /api/case/ask (web on) ===")
    with _client(timeout=180) as client:
        r = client.post(
            f"{BASE}/api/case/ask",
            json={**ASK_BODY, "config": {"model": "DeepSeek-V3", "topK": 4, "enableWebSearch": True}},
        )
    print("status:", r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        return False
    data = r.json()
    assert data.get("refused") is False
    assert data.get("suggestions")
    assert "webCitations" in data
    print(
        "suggestions:", len(data["suggestions"]),
        "citations:", len(data.get("citations") or []),
        "web:", len(data.get("webCitations") or []),
        "literatureMissing:", data.get("literatureMissing"),
    )
    print("web on OK")
    return True


def test_web_search_module():
    print("=== web_search module ===")
    from backend.config import settings
    from backend.retrieval.web_search import search_web

    empty = search_web("孤独症 早期干预", max_results=2)
    assert isinstance(empty, list)
    print("search_web returned list, len=", len(empty))
    if not settings.tavily_api_key:
        assert empty == [], "无 Key 时应降级为空列表"
        print("无 TAVILY_API_KEY，降级为空列表 OK")
    print("web_search module OK")


def test_normalize_literature_missing():
    print("=== _normalize_answer (无文献 + 有网络) ===")
    from backend.routers.consult import _normalize_answer

    web_hits = [
        {"id": "W1", "title": "示例", "url": "https://example.com", "snippet": "摘要"},
    ]
    result = _normalize_answer(
        {"suggestions": []},
        [],
        "年龄：3岁",
        web_hits=web_hits,
        literature_missing=True,
    )
    assert result.get("literatureMissing") is True
    assert result.get("citations") == []
    assert len(result.get("webCitations") or []) == 1
    print("literatureMissing + webCitations OK")


def test_insufficient_no_literature_no_web():
    print("=== insufficient (无文献 + 无网络) ===")
    from backend.routers.consult import _insufficient_response

    result = _insufficient_response("年龄：3岁", reason="未命中文献")
    assert result.get("insufficientLiterature") is True
    assert result.get("webCitations") == []
    print("insufficientLiterature OK")


def main() -> int:
    try:
        with _client(timeout=5) as client:
            client.get(f"{BASE}/api/health").raise_for_status()
    except Exception as exc:
        print(f"后端未启动: {exc}")
        return 1

    test_web_search_module()
    test_normalize_literature_missing()
    test_insufficient_no_literature_no_web()
    test_profile()
    test_refused()
    ok1 = test_ask_web_off()
    ok2 = test_ask_web_on()
    if not (ok1 and ok2):
        print("ask 失败（若未配置 LLM_API_KEY，此为预期）")
        return 2
    print("=== 全部通过 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
