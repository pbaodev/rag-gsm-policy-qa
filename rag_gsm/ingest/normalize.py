"""Chuan hoa van ban va ghi front matter (Buoc 1)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from rag_gsm.schemas import Document

# Vi du: "Cap nhat va co hieu luc ap dung tu ngay: 07/08/2026"
_NGAY_HIEU_LUC_RE = re.compile(
    r"(?:c[oó] hi[eệ]u l[uự]c(?: [aá]p d[uụ]ng)? (?:t[uừ] ng[aà]y|k[eể] t[uừ] ng[aà]y)"
    r"|hi[eệ]u l[uự]c t[uừ] ng[aà]y)\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)


def normalize_nfc(text: str) -> str:
    """Chuan hoa Unicode NFC - chu nhu "e^." co hai dang, khong chuan hoa
    thi BM25 va so khop chuoi truot nhau (bai hoc Buoc 1)."""
    return unicodedata.normalize("NFC", text)


def compute_content_hash(text: str) -> str:
    """sha256 tren van ban da chuan hoa NFC - de bo qua tai lieu khong doi."""
    return hashlib.sha256(normalize_nfc(text).encode("utf-8")).hexdigest()


def extract_ngay_hieu_luc(text: str) -> str | None:
    """Trich ngay hieu luc bang regex. Doi voi cac trang doc tu JSON, ngay
    nay thuong nam ngay dau `description`, khong phai o chan trang - khac
    voi truong hop DOM/OCR van con nhieu chan trang truoc no."""
    m = _NGAY_HIEU_LUC_RE.search(text)
    return m.group(1) if m else None


def make_document(
    *,
    doc_id: str,
    source: str,
    title: str,
    doc_type: str,
    audience: str,
    nguon_tin_cay: str,
    fetched_at: str,
    body_text: str,
    markdown_path: str,
) -> Document:
    """Dung mot Document tu noi dung da trich, tinh san content_hash va
    ngay_hieu_luc."""
    return Document(
        doc_id=doc_id,
        source=source,
        title=title,
        doc_type=doc_type,
        audience=audience,
        nguon_tin_cay=nguon_tin_cay,
        fetched_at=fetched_at,
        content_hash=compute_content_hash(body_text),
        ngay_hieu_luc=extract_ngay_hieu_luc(body_text),
        markdown_path=markdown_path,
    )


def render_markdown_file(doc: Document, body_markdown: str) -> str:
    """Ghep front matter (YAML) + than Markdown thanh noi dung file hoan chinh."""
    front_matter_lines = [
        "---",
        f"source: {doc.source}",
        f"title: {doc.title!r}",
        f"doc_type: {doc.doc_type}",
        f"audience: {doc.audience}",
        f"nguon_tin_cay: {doc.nguon_tin_cay}",
        f"fetched_at: {doc.fetched_at}",
        f"content_hash: {doc.content_hash}",
        f"ngay_hieu_luc: {doc.ngay_hieu_luc if doc.ngay_hieu_luc else 'null'}",
        "---",
        "",
    ]
    body = normalize_nfc(body_markdown)
    return "\n".join(front_matter_lines) + body + "\n"
