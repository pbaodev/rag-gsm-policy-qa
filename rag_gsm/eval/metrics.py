"""Do retrieval: Recall@k va MRR tren gold_chunk_ids, dung lai o 4 tang
(dense-only, BM25-only, sau RRF, sau rerank) - Buoc 9 da chot, ke tiep
cach da do BM25 o Buoc 4."""

from __future__ import annotations


def recall_at_k(gold_chunk_ids: list[str], retrieved_chunk_ids: list[str], k: int) -> float:
    if not gold_chunk_ids:
        raise ValueError("gold_chunk_ids rong - khong tinh duoc recall")
    top_k = set(retrieved_chunk_ids[:k])
    hits = sum(1 for g in gold_chunk_ids if g in top_k)
    return hits / len(gold_chunk_ids)


def mrr(gold_chunk_ids: list[str], retrieved_chunk_ids: list[str]) -> float:
    gold_set = set(gold_chunk_ids)
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in gold_set:
            return 1.0 / rank
    return 0.0
