"""SQLite：已入库文献清单与问答留痕。"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import DB_PATH, ensure_dirs


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                num_chunks INTEGER NOT NULL,
                tag TEXT,
                size_kb INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                profile_json TEXT,
                retrieved_json TEXT,
                answer_json TEXT NOT NULL,
                model TEXT,
                top_k INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def list_documents() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, filename, upload_time, num_chunks, tag, size_kb FROM documents ORDER BY upload_time DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "uploadTime": r["upload_time"],
            "chunks": r["num_chunks"],
            "tag": r["tag"] or "综合指南",
            "sizeKB": r["size_kb"] or 0,
        }
        for r in rows
    ]


def get_stats() -> dict[str, int]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS doc_count, COALESCE(SUM(num_chunks), 0) AS chunk_count FROM documents"
        ).fetchone()
    return {"docCount": row["doc_count"], "chunkCount": row["chunk_count"]}


def insert_document(
    doc_id: str,
    filename: str,
    num_chunks: int,
    tag: str,
    size_kb: int,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO documents (id, filename, upload_time, num_chunks, tag, size_kb)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc_id, filename, now, num_chunks, tag, size_kb),
        )
        conn.commit()


def get_document(doc_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, filename, upload_time, num_chunks, tag, size_kb FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "filename": row["filename"],
        "uploadTime": row["upload_time"],
        "chunks": row["num_chunks"],
        "tag": row["tag"],
        "sizeKB": row["size_kb"],
    }


def insert_qa_log(
    *,
    session_id: str,
    question: str,
    profile: dict[str, Any] | None,
    retrieved: list[dict[str, Any]],
    answer: dict[str, Any],
    model: str,
    top_k: int,
) -> str:
    log_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO qa_logs (
                id, session_id, question, profile_json, retrieved_json,
                answer_json, model, top_k, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                session_id,
                question,
                json.dumps(profile, ensure_ascii=False) if profile else None,
                json.dumps(retrieved, ensure_ascii=False),
                json.dumps(answer, ensure_ascii=False),
                model,
                top_k,
                now,
            ),
        )
        conn.commit()
    return log_id


def delete_document(doc_id: str) -> dict[str, Any] | None:
    doc = get_document(doc_id)
    if not doc:
        return None
    with _connect() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    return doc
