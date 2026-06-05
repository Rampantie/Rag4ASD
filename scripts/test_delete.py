"""删除文献 API 测试。"""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8000"
DOC_ID = sys.argv[1] if len(sys.argv) > 1 else ""


def main() -> int:
    if not DOC_ID:
        print("用法: python scripts/test_delete.py <doc_id>")
        return 1

    with httpx.Client() as client:
        r = client.delete(f"{BASE}/api/documents/{DOC_ID}")
        print(f"DELETE status: {r.status_code}, body: {r.json()}")

        stats = client.get(f"{BASE}/api/stats").json()
        docs = client.get(f"{BASE}/api/documents").json()
        print(f"stats: {stats}")
        print(f"documents: {len(docs)} 条")

    sys.path.insert(0, str(ROOT))
    from backend.chroma_store import get_collection

    col = get_collection()
    result = col.get(where={"doc_id": DOC_ID})
    chroma_count = len(result.get("ids") or [])
    print(f"Chroma remaining chunks for doc: {chroma_count}")

    raw_files = list((ROOT / "data" / "raw").glob(f"{DOC_ID}_*"))
    print(f"raw files remaining: {len(raw_files)}")

    if stats["docCount"] != 0 or stats["chunkCount"] != 0 or len(docs) != 0:
        print("删除后 SQLite 未清空")
        return 1
    if chroma_count != 0:
        print("删除后 Chroma 仍有残留")
        return 1
    if raw_files:
        print("删除后 raw 文件仍存在")
        return 1

    print("=== 删除测试通过 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
