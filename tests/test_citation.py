"""Test rag_gsm.generate.citation - parse/validate [n], danh sach nguon
day du bat ke LLM trich dung hay khong (07-reorder-generation-citation.md)."""

from __future__ import annotations

from rag_gsm.generate.citation import build_citations, extract_cited_numbers, invalid_citations
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="d",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path=f"Duong dan {chunk_id}",
        breadcrumb=f"Duong dan {chunk_id}",
        text="noi dung",
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


def test_extract_cited_numbers_finds_all_brackets():
    assert extract_cited_numbers("Theo [1], va cung theo [3] va [1] lan nua.") == [1, 3, 1]


def test_extract_cited_numbers_empty_when_none():
    assert extract_cited_numbers("khong co trich dan nao") == []


def test_invalid_citations_filters_out_of_range():
    assert invalid_citations([1, 2, 5], valid_max=2) == [5]


def test_build_citations_returns_full_list_regardless_of_what_llm_cited():
    chunks = [_chunk("a"), _chunk("b")]
    citation_map = {1: "a", 2: "b"}
    chunk_lookup = {c.chunk_id: c for c in chunks}

    citations = build_citations(citation_map, chunk_lookup)

    assert [c.n for c in citations] == [1, 2]
    assert [c.chunk_id for c in citations] == ["a", "b"]
    assert citations[0].heading_path == "Duong dan a"
