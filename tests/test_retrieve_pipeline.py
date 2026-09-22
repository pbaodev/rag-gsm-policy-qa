"""Test rag_gsm.retrieve.pipeline - noi hybrid+rerank+fallback that (index
nho, cuc bo, nhu test_hybrid.py) voi Reranker/LLM gia, kiem tra dung ca 3
nhanh: hybrid, pageindex_fallback, khong_biet. Nguong dung DIEM RERANK,
khong phai cosine hay RRF (xem pipeline.py, 05-retrieval.md)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rag_gsm.config import (
    Bm25Config,
    Config,
    ContextConfig,
    EmbeddingConfig,
    FallbackConfig,
    GenerationConfig,
    RerankConfig,
    RrfConfig,
    ThresholdsConfig,
)
from rag_gsm.index.bm25_store import build_bm25_index, load_bm25_index, save_bm25_index
from rag_gsm.index.dense_store import build_table
from rag_gsm.retrieve.pipeline import retrieve_with_fallback
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="test-doc",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path=f"Test > {chunk_id}",
        breadcrumb=f"Test > {chunk_id}",
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


def _config(rerank_pass: float = 0.5, final_k: int = 2) -> Config:
    return Config(
        embedding=EmbeddingConfig(model="fake"),
        bm25=Bm25Config(k1=1.5, b=0.75),
        rrf=RrfConfig(k=60, top_n_per_branch=10),
        rerank=RerankConfig(model="fake", top_k_into_rerank=10),
        context=ContextConfig(final_k=final_k, reorder=True),
        fallback=FallbackConfig(model="fake", excerpt_chars=200),
        generation=GenerationConfig(model="fake", temperature=0.1),
        thresholds=ThresholdsConfig(rerank_pass=rerank_pass),
    )


class FakeEmbedder:
    def embed_query(self, text: str) -> np.ndarray:
        return np.array([1.0, 0.0], dtype="float32")

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class FakeReranker:
    def __init__(self, scores: list[float]):
        self._scores = scores

    def score(self, query: str, texts: list[str]):
        return self._scores[: len(texts)]


class FakeLLM:
    def __init__(self, *, json_response: dict | None = None):
        self.generate_json_calls = 0
        self._json_response = json_response or {"reasoning": "", "node_list": []}

    def generate(self, system: str, user: str) -> str:
        raise NotImplementedError("pipeline khong nen goi generate() - do la viec cua generate_answer()")

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        self.generate_json_calls += 1
        return self._json_response


def _build_index(tmp_path: Path, chunks: list[Chunk]):
    embeddings = np.array([[1.0, 0.0]] * len(chunks), dtype="float32")
    table = build_table(chunks, embeddings, tmp_path / "lancedb")
    bm25 = build_bm25_index([c.text for c in chunks])
    save_bm25_index(bm25, [c.chunk_id for c in chunks], tmp_path / "bm25")
    return table, load_bm25_index(tmp_path / "bm25")


def test_high_rerank_score_takes_hybrid_branch_and_skips_fallback(tmp_path: Path):
    chunks = [_chunk("a", "huy chuyen xe co bi tru tien khong"), _chunk("b", "chinh sach doi tra")]
    table, bm25 = _build_index(tmp_path, chunks)
    chunk_lookup = {c.chunk_id: c for c in chunks}
    llm = FakeLLM()

    result = retrieve_with_fallback(
        "huy chuyen xe co bi tru tien khong",
        embedder=FakeEmbedder(),
        table=table,
        bm25_index=bm25,
        chunk_lookup=chunk_lookup,
        reranker=FakeReranker([0.9, 0.8]),
        llm=llm,
        config=_config(rerank_pass=0.5),
    )

    assert result.branch == "hybrid"
    assert llm.generate_json_calls == 0
    assert len(result.chunks) <= 2
    assert result.trace.threshold == 0.5


def test_low_rerank_score_with_grounded_fallback_takes_pageindex_branch(tmp_path: Path):
    chunks = [_chunk("a", "huy chuyen xe co bi tru tien khong")]
    table, bm25 = _build_index(tmp_path, chunks)
    chunk_lookup = {c.chunk_id: c for c in chunks}
    llm = FakeLLM(
        json_response={
            "reasoning": "...",
            "node_list": [{"chunk_id": "a", "trich_dan": "huy chuyen xe co bi tru tien khong"}],
        }
    )

    result = retrieve_with_fallback(
        "huy chuyen the nao",
        embedder=FakeEmbedder(),
        table=table,
        bm25_index=bm25,
        chunk_lookup=chunk_lookup,
        reranker=FakeReranker([0.1]),
        llm=llm,
        config=_config(rerank_pass=0.5),
    )

    assert result.branch == "pageindex_fallback"
    assert llm.generate_json_calls == 1
    assert [c.chunk_id for c in result.chunks] == ["a"]


def test_low_rerank_score_with_ungrounded_fallback_gives_khong_biet(tmp_path: Path):
    chunks = [_chunk("a", "huy chuyen xe co bi tru tien khong")]
    table, bm25 = _build_index(tmp_path, chunks)
    chunk_lookup = {c.chunk_id: c for c in chunks}
    llm = FakeLLM(json_response={"reasoning": "khong tim thay", "node_list": []})

    result = retrieve_with_fallback(
        "cau hoi khong lien quan gi",
        embedder=FakeEmbedder(),
        table=table,
        bm25_index=bm25,
        chunk_lookup=chunk_lookup,
        reranker=FakeReranker([0.1]),
        llm=llm,
        config=_config(rerank_pass=0.5),
    )

    assert result.branch == "khong_biet"
    assert result.chunks == []


def test_reranker_returning_no_score_goes_straight_to_fallback(tmp_path: Path):
    """FakeReranker tra ve it diem hon so candidate -> rerank_score cua
    candidate do van la None (mac dinh dataclass) -> top_score phai la
    None, khong duoc coi la 'qua nguong', va khong duoc crash khi so sanh
    None >= nguong (bug that de xay ra neu quen check `is not None`)."""
    chunks = [_chunk("a", "noi dung bat ky")]
    table, bm25 = _build_index(tmp_path, chunks)
    chunk_lookup = {c.chunk_id: c for c in chunks}
    llm = FakeLLM(json_response={"reasoning": "", "node_list": []})

    result = retrieve_with_fallback(
        "cau hoi",
        embedder=FakeEmbedder(),
        table=table,
        bm25_index=bm25,
        chunk_lookup=chunk_lookup,
        reranker=FakeReranker([]),
        llm=llm,
        config=_config(rerank_pass=0.5),
    )

    assert result.branch == "khong_biet"
    assert llm.generate_json_calls == 1
