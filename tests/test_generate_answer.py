"""Test rag_gsm.generate.answer - generate_answer() voi LLM gia. Nhanh
'khong_biet' phai KHONG goi LLM (cau tra loi co dinh, hotline/email that)."""

from __future__ import annotations

from rag_gsm.generate.answer import generate_answer
from rag_gsm.schemas import Chunk, RetrievalResult, TraceInfo


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


class FakeLLM:
    def __init__(self, response: str = ""):
        self.calls = 0
        self._response = response

    def generate(self, system: str, user: str) -> str:
        self.calls += 1
        return self._response

    def generate_json(self, system, user, schema_hint):
        raise NotImplementedError


def test_hybrid_branch_calls_llm_and_builds_full_citation_list():
    chunks = [_chunk("a", "noi dung a"), _chunk("b", "noi dung b")]
    retrieval = RetrievalResult(branch="hybrid", chunks=chunks, trace=TraceInfo(branch="hybrid"))
    llm = FakeLLM("Cau tra loi co trich [1].")  # LLM bo sot [2] - van phai co du 2 nguon
    chunk_lookup = {c.chunk_id: c for c in chunks}

    answer = generate_answer("cau hoi", retrieval, llm, chunk_lookup)

    assert llm.calls == 1
    assert answer.branch == "hybrid"
    assert [c.chunk_id for c in answer.citations] == ["a", "b"]
    assert "generate_ms" in retrieval.trace.latency_ms


def test_pageindex_fallback_branch_also_calls_llm():
    chunks = [_chunk("a", "noi dung a")]
    retrieval = RetrievalResult(branch="pageindex_fallback", chunks=chunks, trace=TraceInfo(branch="pageindex_fallback"))
    llm = FakeLLM("Tra loi tu fallback [1].")
    chunk_lookup = {c.chunk_id: c for c in chunks}

    answer = generate_answer("cau hoi", retrieval, llm, chunk_lookup)

    assert llm.calls == 1
    assert answer.branch == "pageindex_fallback"


def test_khong_biet_branch_never_calls_llm_and_uses_real_hotline():
    retrieval = RetrievalResult(branch="khong_biet", chunks=[], trace=TraceInfo(branch="khong_biet"))
    llm = FakeLLM("khong nen thay cau nay")

    answer = generate_answer("cau hoi", retrieval, llm, {})

    assert llm.calls == 0
    assert answer.branch == "khong_biet"
    assert answer.citations == []
    assert "1555" in answer.text
    assert "support.vn@greensm.com" in answer.text
