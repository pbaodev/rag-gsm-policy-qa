"""Test rag_gsm.retrieve.hybrid - reciprocal_rank_fusion() thuan tuy +
hybrid_search() voi LanceDB/bm25s that (nho, cuc bo) va Embedder gia."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rag_gsm.index.bm25_store import build_bm25_index, load_bm25_index, save_bm25_index
from rag_gsm.index.dense_store import build_table
from rag_gsm.retrieve.hybrid import hybrid_search, reciprocal_rank_fusion
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, text: str, doi_tuong: str = "chung") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="test-doc",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path="Test",
        breadcrumb="Test",
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


def test_rrf_combines_ranks_not_raw_scores():
    dense_hits = [("a", 0.99), ("b", 0.5)]
    bm25_hits = [("b", 100.0), ("a", 1.0)]  # b hang 1 o BM25 du diem tho thap hon a nhieu

    result = reciprocal_rank_fusion(dense_hits, bm25_hits, k=60)
    scores = {c.chunk_id: c.rrf_score for c in result}

    assert scores["a"] == scores["b"]


def test_rrf_candidate_in_only_one_branch_still_included():
    dense_hits = [("a", 0.9)]
    bm25_hits = [("b", 5.0)]

    result = reciprocal_rank_fusion(dense_hits, bm25_hits, k=60)

    ids = {c.chunk_id for c in result}
    assert ids == {"a", "b"}
    a = next(c for c in result if c.chunk_id == "a")
    assert a.dense_rank == 1
    assert a.bm25_rank is None


class FakeEmbedder:
    def embed_query(self, text: str) -> np.ndarray:
        return np.array([1.0, 0.0], dtype="float32")

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


def test_hybrid_search_excludes_doi_tac_from_both_branches(tmp_path: Path):
    chunks = [
        _chunk("nguoi_dung#1", "huy chuyen xe co bi tru tien khong", "nguoi_dung"),
        _chunk("doi_tac#1", "huy chuyen xe doi tac bi phat the nao", "doi_tac"),
        _chunk("chung#1", "chinh sach chung ap dung cho tat ca", "chung"),
    ]
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype="float32")
    table = build_table(chunks, embeddings, tmp_path / "lancedb")

    bm25 = build_bm25_index([c.text for c in chunks])
    save_bm25_index(bm25, [c.chunk_id for c in chunks], tmp_path / "bm25")
    bm25_loaded = load_bm25_index(tmp_path / "bm25")

    chunk_lookup = {c.chunk_id: c for c in chunks}
    result = hybrid_search(
        "huy chuyen xe co bi tru tien khong",
        embedder=FakeEmbedder(),
        table=table,
        bm25_index=bm25_loaded,
        chunk_lookup=chunk_lookup,
        top_n_per_branch=10,
    )

    ids = {c.chunk_id for c in result}
    assert "doi_tac#1" not in ids
    assert "nguoi_dung#1" in ids
