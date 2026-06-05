"""一次性入库 API 测试脚本（SSE + 数据校验）。"""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "test_samples" / "asd_sample.txt"
BASE = "http://localhost:8000"


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        line = block.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[5:].strip()))
    return events


def main() -> int:
    if not SAMPLE.exists():
        print(f"缺少测试文件: {SAMPLE}")
        return 1

    print("=== POST /api/documents/ingest ===")
    with SAMPLE.open("rb") as f:
        files = [("files", (SAMPLE.name, f, "text/plain"))]
        data = {"tag": "综合指南", "chunk_size": "200", "overlap": "40"}
        with httpx.Client(timeout=600.0) as client:
            resp = client.post(f"{BASE}/api/documents/ingest", files=files, data=data)

    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:500]}")
        return 1

    events = parse_sse(resp.text)
    stages = [e.get("stage") for e in events if "stage" in e]
    print("SSE stages:", " -> ".join(stages))

    done = next((e for e in events if e.get("done")), None)
    err = next((e for e in events if e.get("error")), None)
    if err:
        print("ERROR:", err.get("message"))
        return 1
    if not done:
        print("未收到 done 事件")
        return 1

    created = done.get("created") or []
    if not created:
        print("created 为空")
        return 1

    doc = created[0]
    doc_id = doc["id"]
    chunks = doc["chunks"]
    print(f"入库成功: id={doc_id}, chunks={chunks}, tag={doc.get('tag')}")

    # API 校验
    with httpx.Client() as client:
        docs = client.get(f"{BASE}/api/documents").json()
        stats = client.get(f"{BASE}/api/stats").json()

    print(f"GET /api/documents: {len(docs)} 条")
    print(f"GET /api/stats: {stats}")

    if stats["docCount"] != 1 or stats["chunkCount"] != chunks:
        print("SQLite 统计不一致")
        return 1

    raw_files = list((ROOT / "data" / "raw").glob(f"{doc_id}_*"))
    if not raw_files:
        print("data/raw 中未找到原始文件")
        return 1
    print(f"原始文件: {raw_files[0].name}")

    # Chroma 校验
    sys.path.insert(0, str(ROOT))
    from backend.chroma_store import get_collection, validate_chunk_metadata

    col = get_collection()
    result = col.get(where={"doc_id": doc_id}, include=["metadatas", "documents"])
    ids = result.get("ids") or []
    print(f"Chroma chunks: {len(ids)}")

    if len(ids) != chunks:
        print("Chroma 块数与 SQLite 不一致")
        return 1

    for meta in result.get("metadatas") or []:
        if not meta.get("source_file"):
            print("缺少 source_file:", meta)
            return 1
        if meta.get("page") is None:
            print("缺少 page:", meta)
            return 1
        if not meta.get("tags"):
            print("缺少 tags:", meta)
            return 1

    issues = validate_chunk_metadata(doc_id)
    if issues:
        print("元数据校验失败:", issues)
        return 1

    print("=== 全部校验通过 ===")
    # 输出 doc_id 供删除测试
    print(f"DOC_ID={doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
