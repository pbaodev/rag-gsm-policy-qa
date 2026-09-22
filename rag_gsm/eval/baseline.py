"""Baseline "nhet het corpus vao prompt" (da hen tu Buoc 3/6, chot o Buoc
9) - di qua DUNG nhanh generation/citation nhu RAG that (cung ep trich
dan [n], cung judge) de so sanh cong bang. KHONG qua retrieve/pipeline.py
- moi chunk (da loc doi_tuong) deu la "ngu canh", khong co khai niem
nhanh hybrid/fallback/khong_biet."""

from __future__ import annotations

from rag_gsm.generate.citation import build_citations, extract_cited_numbers, invalid_citations
from rag_gsm.generate.prompt import build_prompt
from rag_gsm.schemas import Answer, Chunk, LLMAdapter

DEFAULT_DOI_TUONG_ALLOW = ("nguoi_dung", "chung")


def run_baseline(
    query: str,
    chunks: list[Chunk],
    llm: LLMAdapter,
    *,
    doi_tuong_allow: tuple[str, ...] = DEFAULT_DOI_TUONG_ALLOW,
) -> Answer:
    allowed = [c for c in chunks if c.doi_tuong in doi_tuong_allow]
    chunk_lookup = {c.chunk_id: c for c in allowed}

    system, user, citation_map = build_prompt(query, allowed)
    raw_text = llm.generate(system, user)

    bad = invalid_citations(extract_cited_numbers(raw_text), len(allowed))
    if bad:
        print(f"[baseline] canh bao: LLM trich dan so ngoai pham vi 1..{len(allowed)}: {bad}")

    citations = build_citations(citation_map, chunk_lookup)
    return Answer(text=raw_text, citations=citations, branch="baseline")
