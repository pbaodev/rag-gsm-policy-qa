"""Buoc 7: nhan RetrievalResult (dau ra Buoc 5/6), ghep prompt, goi LLM,
tra ve Answer + trich dan. Nhanh 'khong_biet' tra loi CO DINH, khong goi
LLM (khong co chunk nao de dua vao prompt, va cau tra loi da chot san)."""

from __future__ import annotations

import time

from rag_gsm.generate.citation import build_citations, extract_cited_numbers, invalid_citations
from rag_gsm.generate.prompt import KHONG_BIET_TEXT, build_prompt
from rag_gsm.schemas import Answer, Chunk, LLMAdapter, RetrievalResult


def generate_answer(
    query: str, retrieval: RetrievalResult, llm: LLMAdapter, chunk_lookup: dict[str, Chunk]
) -> Answer:
    if retrieval.branch == "khong_biet":
        return Answer(text=KHONG_BIET_TEXT, citations=[], branch="khong_biet")

    system, user, citation_map = build_prompt(query, retrieval.chunks)
    retrieval.trace.citation_map = citation_map

    t0 = time.perf_counter()
    raw_text = llm.generate(system, user)
    retrieval.trace.latency_ms["generate_ms"] = (time.perf_counter() - t0) * 1000

    bad = invalid_citations(extract_cited_numbers(raw_text), len(retrieval.chunks))
    if bad:
        print(f"[generate] canh bao: LLM trich dan so ngoai pham vi 1..{len(retrieval.chunks)}: {bad}")

    citations = build_citations(citation_map, chunk_lookup)
    return Answer(text=raw_text, citations=citations, branch=retrieval.branch)
