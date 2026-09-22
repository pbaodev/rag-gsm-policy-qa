"""Test rag_gsm.chunk.loader - doc lai file .md do normalize.render_markdown_file ghi ra."""

from __future__ import annotations

from pathlib import Path

from rag_gsm.chunk.loader import load_document


def test_load_document_round_trips_front_matter(tmp_path: Path):
    md_path = tmp_path / "vi-du.md"
    md_path.write_text(
        "---\n"
        "source: https://www.greensm.com/vn-vi/test\n"
        "title: 'Quy chế \"đặc biệt\" của Green SM'\n"
        "doc_type: dieu_khoan\n"
        "audience: khach_hang\n"
        "nguon_tin_cay: chinh_thuc\n"
        "fetched_at: 2026-09-22\n"
        "content_hash: abc123\n"
        "ngay_hieu_luc: 07/08/2026\n"
        "---\n"
        "# 1. Nội dung\n\nVăn bản mẫu.\n",
        encoding="utf-8",
    )

    doc, body = load_document(md_path)

    assert doc.doc_id == "vi-du"
    assert doc.title == 'Quy chế "đặc biệt" của Green SM'
    assert doc.doc_type == "dieu_khoan"
    assert doc.ngay_hieu_luc == "07/08/2026"
    assert body.startswith("# 1. Nội dung")


def test_load_document_null_ngay_hieu_luc_becomes_none(tmp_path: Path):
    md_path = tmp_path / "vi-du-2.md"
    md_path.write_text(
        "---\n"
        "source: https://www.greensm.com/vn-vi/test\n"
        "title: 'Không có ngày hiệu lực'\n"
        "doc_type: faq\n"
        "audience: khach_hang\n"
        "nguon_tin_cay: chinh_thuc\n"
        "fetched_at: 2026-09-22\n"
        "content_hash: abc123\n"
        "ngay_hieu_luc: null\n"
        "---\n"
        "# 1. Câu hỏi\n",
        encoding="utf-8",
    )

    doc, _ = load_document(md_path)

    assert doc.ngay_hieu_luc is None
