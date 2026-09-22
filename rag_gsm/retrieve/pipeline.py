"""Noi hybrid_search -> rerank -> nguong -> PageIndex fallback -> sandwich
reorder thanh MOT ham (Buoc 5+6 gop lai), tra ve dung RetrievalResult da
chot trong schemas.py ("Dau ra Buoc 5/6, dau vao Buoc 7").

Nguong dung DIEM RERANK (sigmoid, 0..1), KHONG phai dense cosine va KHONG
phai diem RRF - xem docs/learning/05-retrieval.md dong 8-11 ("Nguong dung
tren diem rerank, khong phai diem RRF... va khong phai cosine tho - da bi
rerank ghi de thu tu"). CLAUDE.md ban dau ghi nham la "dense cosine top-1"
o muc Invariants - da sua lai 2026-09-22 cho khop tai lieu goc.
"""

from __future__ import annotations

import time

from rag_gsm.config import Config
from rag_gsm.retrieve.fallback import run_fallback
from rag_gsm.retrieve.hybrid import hybrid_search
from rag_gsm.retrieve.reorder import sandwich_reorder
from rag_gsm.retrieve.rerank import rerank
from rag_gsm.schemas import Chunk, Embedder, LLMAdapter, RetrievalResult, TraceInfo


def retrieve_with_fallback(
    query: str,
    *,
    embedder: Embedder,
    table,
    bm25_index,
    chunk_lookup: dict[str, Chunk],
    reranker,
    llm: LLMAdapter,
    config: Config,
) -> RetrievalResult:
    latency_ms: dict[str, float] = {}

    t0 = time.perf_counter()
    candidates = hybrid_search(
        query,
        embedder=embedder,
        table=table,
        bm25_index=bm25_index,
        chunk_lookup=chunk_lookup,
        top_n_per_branch=config.rrf.top_n_per_branch,
        rrf_k=config.rrf.k,
    )
    latency_ms["hybrid_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    reranked = rerank(
        query, candidates, chunk_lookup, reranker, top_k_into_rerank=config.rerank.top_k_into_rerank
    )
    latency_ms["rerank_ms"] = (time.perf_counter() - t0) * 1000

    top_score = reranked[0].rerank_score if reranked else None
    passes_threshold = top_score is not None and top_score >= config.thresholds.rerank_pass

    trace = TraceInfo(
        branch="hybrid",
        candidates_before_rerank=candidates,
        candidates_after_rerank=reranked,
        threshold=config.thresholds.rerank_pass,
    )

    if passes_threshold:
        selected = [chunk_lookup[c.chunk_id] for c in reranked[: config.context.final_k]]
    else:
        t0 = time.perf_counter()
        fb = run_fallback(query, list(chunk_lookup.values()), llm, excerpt_chars=config.fallback.excerpt_chars)
        latency_ms["fallback_ms"] = (time.perf_counter() - t0) * 1000
        trace.fallback_outline_size = len(chunk_lookup)
        trace.fallback_node_list = fb.node_list

        if not fb.du_bang_chung:
            trace.branch = "khong_biet"
            trace.latency_ms = latency_ms
            return RetrievalResult(branch="khong_biet", chunks=[], trace=trace)

        trace.branch = "pageindex_fallback"
        selected = [chunk_lookup[node["chunk_id"]] for node in fb.node_list][: config.context.final_k]

    if config.context.reorder:
        selected = sandwich_reorder(selected)

    trace.latency_ms = latency_ms
    return RetrievalResult(branch=trace.branch, chunks=selected, trace=trace)
