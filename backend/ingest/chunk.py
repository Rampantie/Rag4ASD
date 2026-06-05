"""文本分块，保留来源元数据。"""

from dataclasses import dataclass


@dataclass
class TextChunk:
    text: str
    page: int | None
    section: str | None
    chunk_index: int


def chunk_segments(
    segments: list[dict],
    *,
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    """对抽取段落按字符窗口分块。"""
    if chunk_size < 50:
        raise ValueError("chunk_size 过小")
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    chunks: list[TextChunk] = []
    idx = 0

    for seg in segments:
        text = seg["text"]
        page = seg.get("page")
        section = seg.get("section")
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    TextChunk(
                        text=piece,
                        page=page,
                        section=section,
                        chunk_index=idx,
                    )
                )
                idx += 1
            if end >= len(text):
                break
            start = end - overlap

    return chunks
