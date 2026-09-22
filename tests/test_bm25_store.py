"""Test rag_gsm.index.bm25_store - khong fetch mang, chi dung bm25s local."""

from __future__ import annotations

from pathlib import Path

from rag_gsm.index.bm25_store import (
    build_bm25_index,
    load_bm25_index,
    save_bm25_index,
    search,
    strip_diacritics,
    tokenize,
)


def test_strip_diacritics_maps_d_with_stroke():
    assert strip_diacritics("Đối tác") == "doi tac"


def test_strip_diacritics_removes_tone_marks():
    assert strip_diacritics("hủy chuyến xe") == "huy chuyen xe"


def test_tokenize_splits_on_punctuation():
    assert tokenize("Hủy chuyến, có bị trừ tiền không?") == [
        "huy",
        "chuyen",
        "co",
        "bi",
        "tru",
        "tien",
        "khong",
    ]


def test_search_finds_diacritic_free_query_after_diacritic_corpus(tmp_path: Path):
    """Dung khong dau van tim ra van ban co dau - dung invariant Buoc 4
    (MRR 0,94 ca cau khong dau)."""
    texts = [
        "Hủy chuyến xe có bị trừ tiền không",
        "Làm sao để đặt xe trên ứng dụng",
        "Chính sách hoàn tiền khi hủy chuyến",
    ]
    chunk_ids = ["faq#1", "faq#2", "faq#3"]

    bm25 = build_bm25_index(texts)
    save_bm25_index(bm25, chunk_ids, tmp_path / "bm25")
    loaded = load_bm25_index(tmp_path / "bm25")

    hits = search(loaded, "huy chuyen xe co bi tru tien khong", top_k=2)

    assert hits[0][0] == "faq#1"
