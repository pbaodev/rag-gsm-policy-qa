"""Test rag_gsm.retrieve.fallback - dung LLMAdapter gia (test double);
generate/llm_adapter.py (Ollama/Claude that) chua xay, dung thu tu build
ingest -> index -> retrieve -> generate (kien-truc-code.md)."""

from __future__ import annotations

from rag_gsm.retrieve.fallback import build_outline, run_fallback
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, text: str, doi_tuong: str = "chung") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="test-doc",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path="Test",
        breadcrumb=f"Test › {chunk_id}",
        text=text,
        so_muc="1",
        doi_tuong=doi_tuong,
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        ngay_hieu_luc=None,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk="dieu_khoan",
        source="https://www.greensm.com/vn-vi/test",
        token_count=5,
    )


class FakeLLM:
    def __init__(self, response: dict):
        self._response = response

    def generate(self, system: str, user: str) -> str:
        raise NotImplementedError

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        return self._response


def test_grounded_citation_is_kept():
    chunks = [_chunk("faq#1", "Ban co the huy chuyen mien phi trong 2 phut dau.")]
    llm = FakeLLM(
        {
            "reasoning": "co dieu khoan lien quan",
            "node_list": [{"chunk_id": "faq#1", "trich_dan": "huy chuyen mien phi trong 2 phut dau"}],
        }
    )

    result = run_fallback("huy chuyen co mat phi khong", chunks, llm)

    assert result.du_bang_chung is True
    assert result.node_list == [{"chunk_id": "faq#1", "trich_dan": "huy chuyen mien phi trong 2 phut dau"}]


def test_hallucinated_citation_is_rejected():
    """trich_dan khong khop nguyen van chunk -> khong du bang chung, di
    nhanh 'khong biet' - dung invariant 06-pageindex-fallback.md."""
    chunks = [_chunk("faq#1", "Ban co the huy chuyen mien phi trong 2 phut dau.")]
    llm = FakeLLM(
        {"reasoning": "...", "node_list": [{"chunk_id": "faq#1", "trich_dan": "cau nay khong co trong chunk that"}]}
    )

    result = run_fallback("cau hoi", chunks, llm)

    assert result.du_bang_chung is False
    assert result.node_list == []


def test_empty_node_list_is_not_enough_evidence():
    chunks = [_chunk("faq#1", "noi dung bat ky")]
    llm = FakeLLM({"reasoning": "khong tim thay", "node_list": []})

    result = run_fallback("cau hoi", chunks, llm)

    assert result.du_bang_chung is False


def test_build_outline_only_includes_given_chunks():
    chunks = [_chunk("nguoi_dung#1", "dieu khoan cho nguoi dung", "nguoi_dung")]
    outline = build_outline(chunks)
    assert outline == [{"chunk_id": "nguoi_dung#1", "breadcrumb": "Test › nguoi_dung#1", "doan_trich": "dieu khoan cho nguoi dung"}]


def test_run_fallback_filters_doi_tac_before_building_outline():
    """Ngay ca khi LLM 'chon' dung mot chunk doi_tac va trich nguyen van
    dung, van phai bi loai vi chunk do khong duoc dua vao outline tu dau -
    cung bo loc doi_tuong nhu nhanh hybrid (CLAUDE.md invariant)."""
    chunks = [
        _chunk("nguoi_dung#1", "dieu khoan cho nguoi dung ve huy chuyen", "nguoi_dung"),
        _chunk("doi_tac#1", "dieu khoan cho doi tac ve huy chuyen", "doi_tac"),
    ]
    llm = FakeLLM(
        {
            "reasoning": "...",
            "node_list": [{"chunk_id": "doi_tac#1", "trich_dan": "dieu khoan cho doi tac ve huy chuyen"}],
        }
    )

    result = run_fallback("huy chuyen the nao", chunks, llm)

    assert result.du_bang_chung is False
    assert result.node_list == []
