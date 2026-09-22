"""RRF (Cormack, Clarke, Buttcher 2009), Buoc 5 da chot: gop dense + BM25
theo THU HANG, khong theo diem tho (khong so sanh duoc thang cosine vs
BM25 - bai hoc Buoc 0). k=60, top-20 moi nhanh, khong trong so.

BM25 (bm25s) khong ho tro loc metadata truoc khi xep hang nhu LanceDB
(khong co "prefilter") - day la mot khoang trong 05-retrieval.md khong
noi toi. Bu lai bang cach lay du du roi loc doi_tuong SAU o nhanh BM25;
chap nhan duoc vi bm25s tinh diem CHINH XAC tren toan bo tu vung (khong
xap xi/ANN nhu dense), va corpus chi vai tram chunk nen lay du du rat re.
"""

from __future__ import annotations

from rag_gsm.index.bm25_store import search as bm25_search
from rag_gsm.index.dense_store import search as dense_search
from rag_gsm.schemas import Chunk, Embedder, RetrievalCandidate

DEFAULT_DOI_TUONG_ALLOW = ("nguoi_dung", "chung")
_OVERFETCH_FACTOR = 5


def reciprocal_rank_fusion(
    dense_hits: list[tuple[str, float]],
    bm25_hits: list[tuple[str, float]],
    *,
    k: int = 60,
) -> list[RetrievalCandidate]:
    candidates: dict[str, RetrievalCandidate] = {}

    for rank, (chunk_id, score) in enumerate(dense_hits, start=1):
        c = candidates.setdefault(chunk_id, RetrievalCandidate(chunk_id=chunk_id))
        c.dense_score, c.dense_rank = score, rank

    for rank, (chunk_id, score) in enumerate(bm25_hits, start=1):
        c = candidates.setdefault(chunk_id, RetrievalCandidate(chunk_id=chunk_id))
        c.bm25_score, c.bm25_rank = score, rank

    for c in candidates.values():
        rrf = 0.0
        if c.dense_rank is not None:
            rrf += 1.0 / (k + c.dense_rank)
        if c.bm25_rank is not None:
            rrf += 1.0 / (k + c.bm25_rank)
        c.rrf_score = rrf

    return sorted(candidates.values(), key=lambda c: c.rrf_score, reverse=True)


def hybrid_search(
    query: str,
    *,
    embedder: Embedder,
    table,
    bm25_index,
    chunk_lookup: dict[str, Chunk],
    doi_tuong_allow: tuple[str, ...] = DEFAULT_DOI_TUONG_ALLOW,
    top_n_per_branch: int = 20,
    rrf_k: int = 60,
) -> list[RetrievalCandidate]:
    allow_sql = "doi_tuong IN (" + ", ".join(f"'{d}'" for d in doi_tuong_allow) + ")"

    query_vector = embedder.embed_query(query)
    dense_rows = dense_search(table, query_vector, top_n_per_branch, filter_sql=allow_sql)
    dense_hits = [(row["chunk_id"], row["similarity"]) for row in dense_rows]

    overfetch_k = min(len(chunk_lookup), top_n_per_branch * _OVERFETCH_FACTOR)
    raw_bm25_hits = bm25_search(bm25_index, query, top_k=overfetch_k)
    bm25_hits = [
        (chunk_id, score)
        for chunk_id, score in raw_bm25_hits
        if chunk_lookup[chunk_id].doi_tuong in doi_tuong_allow
    ][:top_n_per_branch]

    return reciprocal_rank_fusion(dense_hits, bm25_hits, k=rrf_k)
