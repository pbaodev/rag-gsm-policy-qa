"""Doc lai file Markdown ma ingest da ghi (front matter + than) thanh Document + body.

Ngược với `normalize.render_markdown_file` (Buoc 1): front matter la cac
dong `key: value` don gian, gia tri chuoi dung Python repr (`!r`) nen doc
lai bang `ast.literal_eval` thay vi tu tach dau nhay.
"""

from __future__ import annotations

import ast
from pathlib import Path

from rag_gsm.schemas import Document


def _unquote(value: str) -> str:
    if value and value[0] in "'\"":
        return ast.literal_eval(value)
    return value


def load_document(md_path: Path) -> tuple[Document, str]:
    """Tra ve (Document, than Markdown) tu 1 file da ingest ghi ra."""
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{md_path}: khong co front matter dang '---'")
    _, front, body = text.split("---\n", 2)

    fields: dict[str, str] = {}
    for line in front.strip("\n").split("\n"):
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    doc = Document(
        doc_id=md_path.stem,
        source=fields["source"],
        title=_unquote(fields["title"]),
        doc_type=fields["doc_type"],
        audience=fields["audience"],
        nguon_tin_cay=fields["nguon_tin_cay"],
        fetched_at=fields["fetched_at"],
        content_hash=fields["content_hash"],
        ngay_hieu_luc=None if fields["ngay_hieu_luc"] == "null" else fields["ngay_hieu_luc"],
        markdown_path=str(md_path),
    )
    return doc, body.strip("\n")
