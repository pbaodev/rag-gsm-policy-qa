"""Test rag_gsm.eval.metrics - Recall@k va MRR thuan tuy."""

from __future__ import annotations

import pytest

from rag_gsm.eval.metrics import mrr, recall_at_k


def test_recall_at_k_all_gold_found():
    assert recall_at_k(["a", "b"], ["a", "b", "c"], k=3) == 1.0


def test_recall_at_k_partial():
    assert recall_at_k(["a", "b"], ["a", "c", "d"], k=3) == 0.5


def test_recall_at_k_respects_k_cutoff():
    assert recall_at_k(["a"], ["b", "c", "a"], k=2) == 0.0


def test_recall_at_k_empty_gold_raises():
    with pytest.raises(ValueError):
        recall_at_k([], ["a"], k=3)


def test_mrr_first_position():
    assert mrr(["a"], ["a", "b"]) == 1.0


def test_mrr_second_position():
    assert mrr(["a"], ["b", "a"]) == 0.5


def test_mrr_not_found_is_zero():
    assert mrr(["a"], ["b", "c"]) == 0.0


def test_mrr_any_gold_match_counts():
    assert mrr(["a", "b"], ["c", "b", "a"]) == 0.5
