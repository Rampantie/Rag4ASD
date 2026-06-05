"""Chroma 向量库：literature 集合读写。"""

from functools import lru_cache
from typing import Any

import chromadb

from backend.config import CHROMA_DIR, COLLECTION_NAME, ensure_dirs, settings


@lru_cache
def get_collection():
    ensure_dirs()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    *,
    doc_id: str,
    source_file: str,
    tag: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    collection = get_collection()
    ids = [f"{doc_id}_{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "source_file": source_file,
            "page": c["page"] if c["page"] is not None else -1,
            "section": c["section"] or "",
            "tags": tag,
            "chunk_id": ids[i],
            "chunk_index": c["chunk_index"],
        }
        for i, c in enumerate(chunks)
    ]
    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def delete_by_doc_id(doc_id: str) -> int:
    collection = get_collection()
    existing = collection.get(where={"doc_id": doc_id})
    ids = existing.get("ids") or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def count_chunks() -> int:
    collection = get_collection()
    return collection.count()


def search_literature(*, query_embedding: list[float], top_k: int) -> list[dict]:
    """向量检索 literature 集合，返回带出处信息的片段。"""
    collection = get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[dict] = []
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    max_dist = settings.retrieval_max_distance

    for doc_text, meta, dist in zip(docs, metas, dists):
        if dist is not None and dist > max_dist:
            continue
        page = meta.get("page")
        if page is not None and int(page) > 0:
            loc = f"p.{page}"
        elif meta.get("section"):
            loc = str(meta.get("section"))
        else:
            loc = "未知位置"

        chunks.append(
            {
                "source": meta.get("source_file") or "未知文献",
                "loc": loc,
                "snippet": doc_text,
                "doc_id": meta.get("doc_id"),
                "chunk_id": meta.get("chunk_id"),
                "tags": meta.get("tags") or "",
            }
        )
    return chunks


def validate_chunk_metadata(doc_id: str) -> list[str]:
    """检查入库块是否具备溯源元数据，返回缺失项描述。"""
    collection = get_collection()
    result = collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    issues: list[str] = []
    for meta in result.get("metadatas") or []:
        if not meta.get("source_file"):
            issues.append(f"chunk {meta.get('chunk_id')} 缺少 source_file")
        if meta.get("page") is None:
            issues.append(f"chunk {meta.get('chunk_id')} 缺少 page")
    return issues
