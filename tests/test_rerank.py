"""Test rag_gsm.retrieve.rerank - chi test ham rerank() (sap xep, cat
top-k) bang mot reranker gia. VietnameseReranker that (model + tokenizer
da sua qua subprocess) chua co test offline - cung ly do embedder.py
chua co test offline (can tai model that)."""

from __future__ import annotations

from rag_gsm.retrieve.rerank import rerank
from rag_gsm.schemas import Chunk, RetrievalCandidate


def _chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="test-doc",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path="Test",
        breadcrumb="Test",
        text=f"noi dung {chunk_id}",
        so_muc="1",
        doi_tuong="chung",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        ngay_hieu_luc=None,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk="dieu_khoan",
        source="https://www.greensm.com/vn-vi/test",
        token_count=3,
    )


class FakeReranker:
    def __init__(self, scores: list[float]):
        self._scores = scores

    def score(self, query: str, texts: list[str]):
        return self._scores


def test_rerank_reorders_by_score_descending():
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    chunk_lookup = {c.chunk_id: c for c in chunks}
    candidates = [RetrievalCandidate(chunk_id=c.chunk_id, rrf_score=1.0) for c in chunks]

    result = rerank("cau hoi", candidates, chunk_lookup, FakeReranker([0.1, 0.9, 0.5]))

    assert [c.chunk_id for c in result] == ["b", "c", "a"]
    assert result[0].rerank_score == 0.9


def test_rerank_truncates_to_top_k_into_rerank():
    chunks = [_chunk(str(i)) for i in range(5)]
    chunk_lookup = {c.chunk_id: c for c in chunks}
    candidates = [RetrievalCandidate(chunk_id=c.chunk_id) for c in chunks]

    result = rerank("q", candidates, chunk_lookup, FakeReranker([0.5, 0.5]), top_k_into_rerank=2)

    assert len(result) == 2


def test_rerank_empty_candidates_returns_empty():
    assert rerank("q", [], {}, FakeReranker([])) == []
