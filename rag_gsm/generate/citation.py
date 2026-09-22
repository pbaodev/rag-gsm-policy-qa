"""Trich dan theo so thu tu [n] khop thu tu khoi ngu canh trong prompt
(Buoc 7 da chot), khong phai chunk_id that - xem prompt.py. Danh sach
nguon tra ve luon DAY DU theo citation_map bat ke LLM co chen dung [n]
hay khong - luoi an toan thu hai, khong chan cau tra loi vi thieu/sai so."""

from __future__ import annotations

import re

from rag_gsm.schemas import Chunk, Citation

_CITATION_RE = re.compile(r"\[(\d+)\]")


def extract_cited_numbers(text: str) -> list[int]:
    return [int(n) for n in _CITATION_RE.findall(text)]


def invalid_citations(cited_numbers: list[int], valid_max: int) -> list[int]:
    return [n for n in cited_numbers if not (1 <= n <= valid_max)]


def build_citations(citation_map: dict[int, str], chunk_lookup: dict[str, Chunk]) -> list[Citation]:
    citations = []
    for n in sorted(citation_map):
        chunk = chunk_lookup[citation_map[n]]
        citations.append(
            Citation(
                n=n,
                chunk_id=chunk.chunk_id,
                source=chunk.source,
                heading_path=chunk.heading_path,
                trang=chunk.trang_bat_dau,
            )
        )
    return citations
