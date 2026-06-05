"""文档文本抽取：PDF / Word / txt。"""

from pathlib import Path


class ExtractError(Exception):
    pass


def extract_document(path: Path) -> list[dict]:
    """
    返回按页/段落划分的文本段。
    每项: {"text": str, "page": int|None, "section": str|None}
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in (".doc", ".docx"):
        return _extract_docx(path)
    if suffix == ".txt":
        return _extract_txt(path)
    raise ExtractError(f"不支持的文件格式: {suffix}")


def _extract_pdf(path: Path) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    segments: list[dict] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append({"text": text, "page": i, "section": None})
    if not segments:
        raise ExtractError(
            "该 PDF 为扫描件或图片型文档，无法直接抽取文字。"
            "请将报告转为可选中文本的 Word/txt 后上传，或跳过上传、在页面手动填写个案信息。"
        )
    return segments


def _extract_docx(path: Path) -> list[dict]:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise ExtractError("Word 文档为空或无法读取")
    return [{"text": "\n".join(paragraphs), "page": None, "section": "全文"}]


def _extract_txt(path: Path) -> list[dict]:
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            text = path.read_text(encoding=encoding).strip()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ExtractError("txt 文件编码无法识别")
    if not text:
        raise ExtractError("txt 文件为空")
    return [{"text": text, "page": None, "section": "全文"}]
