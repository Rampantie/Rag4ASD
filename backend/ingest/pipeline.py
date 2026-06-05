"""文献入库管道：保存 → 抽取 → 分块 → 嵌入 → 写 Chroma + SQLite。"""

import shutil
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from backend import db
from backend.chroma_store import add_chunks, delete_by_doc_id, validate_chunk_metadata
from backend.config import RAW_DIR, ensure_dirs
from backend.ingest.chunk import chunk_segments
from backend.ingest.extract import ExtractError, extract_document
from backend.llm.embedding import get_embedding_client

ProgressFn = Callable[[dict[str, Any]], None]
EMBED_BATCH = 16


def _progress(
    on_progress: ProgressFn | None,
    *,
    file_index: int,
    total: int,
    filename: str,
    stage: str,
    detail: str,
) -> dict[str, Any]:
    event = {
        "fileIndex": file_index,
        "total": total,
        "filename": filename,
        "stage": stage,
        "detail": detail,
    }
    if on_progress:
        on_progress(event)
    return event


def _ingest_one(
    filename: str,
    src_path: Path,
    *,
    file_index: int,
    total: int,
    tag: str,
    chunk_size: int,
    overlap: int,
    on_progress: ProgressFn | None,
) -> dict[str, Any]:
    ensure_dirs()
    client = get_embedding_client()
    doc_id = str(uuid.uuid4())
    dest = RAW_DIR / f"{doc_id}_{filename}"
    shutil.copy2(src_path, dest)
    size_kb = max(1, round(dest.stat().st_size / 1024))

    try:
        _progress(on_progress, file_index=file_index, total=total, filename=filename, stage="抽取", detail=f"解析 {filename}")
        segments = extract_document(dest)

        _progress(
            on_progress,
            file_index=file_index,
            total=total,
            filename=filename,
            stage="分块",
            detail=f"chunk={chunk_size} 重叠={overlap}",
        )
        text_chunks = chunk_segments(segments, chunk_size=chunk_size, overlap=overlap)
        if not text_chunks:
            raise ExtractError("分块结果为空")

        chunk_dicts = [
            {"text": c.text, "page": c.page, "section": c.section, "chunk_index": c.chunk_index}
            for c in text_chunks
        ]
        _progress(
            on_progress,
            file_index=file_index,
            total=total,
            filename=filename,
            stage="分块",
            detail=f"共 {len(chunk_dicts)} 块",
        )

        all_embeddings: list[list[float]] = []
        for batch_start in range(0, len(chunk_dicts), EMBED_BATCH):
            batch = chunk_dicts[batch_start : batch_start + EMBED_BATCH]
            batch_no = batch_start // EMBED_BATCH + 1
            batch_total = (len(chunk_dicts) + EMBED_BATCH - 1) // EMBED_BATCH
            _progress(
                on_progress,
                file_index=file_index,
                total=total,
                filename=filename,
                stage="嵌入",
                detail=f"向量化第 {batch_no}/{batch_total} 批（{len(batch)} 块）",
            )
            all_embeddings.extend(client.embed([c["text"] for c in batch]))

        _progress(
            on_progress,
            file_index=file_index,
            total=total,
            filename=filename,
            stage="写库",
            detail="写入向量库 literature 集合",
        )
        add_chunks(
            doc_id=doc_id,
            source_file=filename,
            tag=tag,
            chunks=chunk_dicts,
            embeddings=all_embeddings,
        )

        issues = validate_chunk_metadata(doc_id)
        if issues:
            raise ExtractError(f"元数据校验失败: {issues[0]}")

        db.insert_document(doc_id, filename, len(chunk_dicts), tag, size_kb)
        doc = db.get_document(doc_id)
        if not doc:
            raise ExtractError("SQLite 写入失败")
        return doc

    except Exception:
        delete_by_doc_id(doc_id)
        dest.unlink(missing_ok=True)
        raise


def ingest_files(
    file_paths: list[tuple[str, Path]],
    *,
    tag: str,
    chunk_size: int,
    overlap: int,
    on_progress: ProgressFn | None = None,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    total = len(file_paths)
    for i, (filename, path) in enumerate(file_paths):
        created.append(
            _ingest_one(
                filename,
                path,
                file_index=i,
                total=total,
                tag=tag,
                chunk_size=chunk_size,
                overlap=overlap,
                on_progress=on_progress,
            )
        )
    return created


def ingest_files_iter(
    file_paths: list[tuple[str, Path]],
    *,
    tag: str,
    chunk_size: int,
    overlap: int,
) -> Iterator[dict[str, Any]]:
    """生成器：逐条 yield 进度事件，最后 yield done / error。"""
    created: list[dict[str, Any]] = []
    total = len(file_paths)
    try:
        for i, (filename, path) in enumerate(file_paths):
            events: list[dict[str, Any]] = []

            def capture(event: dict[str, Any]) -> None:
                events.append(event)

            doc = _ingest_one(
                filename,
                path,
                file_index=i,
                total=total,
                tag=tag,
                chunk_size=chunk_size,
                overlap=overlap,
                on_progress=capture,
            )
            for evt in events:
                yield evt
            created.append(doc)

        yield {"done": True, "created": created, "totalChunks": sum(d["chunks"] for d in created)}
    except Exception as exc:
        yield {"error": True, "message": str(exc)}


def remove_document(doc_id: str) -> bool:
    doc = db.delete_document(doc_id)
    if not doc:
        return False
    delete_by_doc_id(doc_id)
    for p in RAW_DIR.glob(f"{doc_id}_*"):
        p.unlink(missing_ok=True)
    return True
