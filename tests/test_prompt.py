"""Test rag_gsm.generate.prompt - build_prompt() thuan tuy sap xep."""

from __future__ import annotations

from rag_gsm.generate.prompt import build_prompt
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="d",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path=f"Duong dan {chunk_id}",
        breadcrumb=f"Duong dan {chunk_id}",
        text=text,
        so_muc="1",
        doi_tuong="chung",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        ngay_hieu_luc=None,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk="dieu_khoan",
        source="https://www.greensm.com/vn-vi/test",
        token_count=5,
    )


def test_citation_map_matches_prompt_order_not_chunk_id():
    chunks = [_chunk("z9", "noi dung z9"), _chunk("a1", "noi dung a1")]

    _, user, citation_map = build_prompt("cau hoi", chunks)

    assert citation_map == {1: "z9", 2: "a1"}
    assert "[1]" in user
    assert "[2]" in user
    assert "noi dung z9" in user
    assert "noi dung a1" in user


def test_empty_chunks_gives_empty_citation_map():
    _, user, citation_map = build_prompt("cau hoi", [])
    assert citation_map == {}
    assert "cau hoi" in user


def test_system_prompt_mentions_citation_bracket_example():
    system, _, _ = build_prompt("cau hoi", [])
    assert "[1]" in system
