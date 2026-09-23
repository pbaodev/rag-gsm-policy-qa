"""Chay toan bo extractor JSON da co (general, privacy, insurance, faq,
egreen) va ghi ra data/markdown/<doc_id>.md.

Chua bao gom: OCR Quy che hoat dong (can Docling, viec rieng - xem
rag_gsm/ingest/ocr_regulations.py), Hop dong dich vu (ngoai pham vi
khach hang).

Chay: uv run python -m rag_gsm.ingest.run
"""

from __future__ import annotations

from pathlib import Path

from rag_gsm.ingest import heading
from rag_gsm.ingest.extractors import egreen, faq, general, insurance, privacy
from rag_gsm.ingest.normalize import render_markdown_file
from rag_gsm.schemas import Document

MARKDOWN_DIR = Path("data/markdown")


def _write(doc: Document, body_md: str) -> None:
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    Path(doc.markdown_path).write_text(render_markdown_file(doc, body_md), encoding="utf-8")


def main() -> None:
    print("== general (Dieu khoan su dung + Phu luc, 15/16 - bo qua muc trung voi privacy) ==")
    for doc, body_md in general.extract():
        _write(doc, body_md)
        warnings = heading.check_numbering_continuity(body_md)
        flag = f"  !! {warnings[0]}" if warnings else ""
        print(
            f"  {doc.doc_id:38s} {len(body_md):7d} ky tu  "
            f"ngay_hieu_luc={doc.ngay_hieu_luc}{flag}"
        )

    print("== privacy (Chinh sach bao ve du lieu ca nhan, 14 muc) ==")
    doc, body_md = privacy.extract()
    _write(doc, body_md)
    print(f"  {doc.doc_id:38s} {len(body_md):7d} ky tu  ngay_hieu_luc={doc.ngay_hieu_luc}")

    print("== insurance (Bao hiem khach hang) ==")
    doc, body_md = insurance.extract()
    _write(doc, body_md)
    print(f"  {doc.doc_id:38s} {len(body_md):7d} ky tu")

    print("== faq (Trung tam giai dap - Danh cho nguoi dung) ==")
    doc, body_md = faq.extract()
    _write(doc, body_md)
    n_h1 = sum(1 for ln in body_md.splitlines() if ln.startswith("# "))
    n_h2 = sum(1 for ln in body_md.splitlines() if ln.startswith("## "))
    print(f"  {doc.doc_id:38s} {len(body_md):7d} ky tu  {n_h1} danh muc, {n_h2} cau hoi")

    print("== egreen (Dieu khoan ve The/Vi E-Green) ==")
    doc, body_md = egreen.extract()
    _write(doc, body_md)
    warnings = heading.check_numbering_continuity(body_md)
    flag = f"  !! {warnings[0]}" if warnings else ""
    print(f"  {doc.doc_id:38s} {len(body_md):7d} ky tu{flag}")


if __name__ == "__main__":
    main()
