"""BM25 qua bm25s (Buoc 4 da chot): tach am tiet BO DAU, mot chi muc -
MRR 0,94 ca cau co dau lan khong dau (xem docs/learning/04-index.md)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import bm25s

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def strip_diacritics(text: str) -> str:
    """NFD tach dau roi bo cac ky tu category Mn (dau), rieng 'd' phai
    map tay vi khong tach duoc bang NFD (la 1 ky tu Unicode doc lap,
    khong phai d + dau)."""
    text = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(strip_diacritics(text))


def build_bm25_index(texts: list[str], *, k1: float = 1.5, b: float = 0.75) -> bm25s.BM25:
    corpus_tokens = [tokenize(t) for t in texts]
    bm25 = bm25s.BM25(k1=k1, b=b)
    bm25.index(corpus_tokens, show_progress=False)
    return bm25


def save_bm25_index(bm25: bm25s.BM25, chunk_ids: list[str], save_dir: Path) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    bm25.save(str(save_dir), corpus=chunk_ids, show_progress=False)


def load_bm25_index(save_dir: Path) -> bm25s.BM25:
    return bm25s.BM25.load(str(save_dir), load_corpus=True, show_progress=False)


def search(bm25: bm25s.BM25, query: str, top_k: int) -> list[tuple[str, float]]:
    """Tra ve (chunk_id, diem) - dung de kiem tra chi muc, KHONG phai
    duong truy hoi cuoi cung (RRF/hybrid la viec cua Buoc 5, module retrieve/)."""
    query_tokens = [tokenize(query)]
    k = min(top_k, bm25.scores["num_docs"])
    results, scores = bm25.retrieve(query_tokens, k=k, show_progress=False)
    hits = []
    for doc, score in zip(results[0], scores[0]):
        chunk_id = doc["text"] if isinstance(doc, dict) else doc
        hits.append((chunk_id, float(score)))
    return hits
