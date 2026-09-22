from rag_gsm.retrieve.reorder import sandwich_reorder


def test_sandwich_reorder_matches_documented_example():
    assert sandwich_reorder(["A", "B", "C"]) == ["A", "C", "B"]


def test_sandwich_reorder_four_items():
    assert sandwich_reorder(["A", "B", "C", "D"]) == ["A", "C", "D", "B"]


def test_sandwich_reorder_single_item():
    assert sandwich_reorder(["A"]) == ["A"]


def test_sandwich_reorder_empty():
    assert sandwich_reorder([]) == []
