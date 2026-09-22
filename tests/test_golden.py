"""Test rag_gsm.eval.golden - load_golden_questions() doc jsonl that."""

from __future__ import annotations

from pathlib import Path

from rag_gsm.eval.golden import load_golden_questions


def test_load_golden_questions_parses_all_fields(tmp_path: Path):
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"id": "q1", "cau_hoi": "cau hoi 1", "chu_de": "huy chuyen", "do_kho": "khop_tieu_de", '
        '"nhanh_ky_vong": "hybrid", "gold_chunk_ids": ["faq#1"], "gold_answer": "dap an", "ghi_chu": ""}\n',
        encoding="utf-8",
    )

    questions = load_golden_questions(path)

    assert len(questions) == 1
    assert questions[0].id == "q1"
    assert questions[0].gold_chunk_ids == ["faq#1"]


def test_load_golden_questions_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"id": "q1", "cau_hoi": "c1", "chu_de": "t", "do_kho": "khop_tieu_de", "nhanh_ky_vong": "hybrid", '
        '"gold_chunk_ids": ["a"], "gold_answer": "x", "ghi_chu": ""}\n\n',
        encoding="utf-8",
    )

    questions = load_golden_questions(path)

    assert len(questions) == 1


def test_real_golden_questions_file_loads_and_has_50_entries():
    """Kiem tra file that trong repo (eval/golden_questions.jsonl) van
    parse duoc dung schema - bat loi that neu ai do sua tay lam hong dinh
    dang, khong can mang/model nao."""
    questions = load_golden_questions()

    assert len(questions) == 50
    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids)), "id cau hoi bi trung"
    for q in questions:
        assert q.nhanh_ky_vong in ("hybrid", "pageindex_fallback", "khong_biet")
        if q.nhanh_ky_vong == "khong_biet":
            assert q.gold_chunk_ids == [], f"{q.id}: khong_biet nhung van co gold_chunk_ids"
        else:
            assert q.gold_chunk_ids, f"{q.id}: nhanh {q.nhanh_ky_vong} nhung khong co gold_chunk_ids"
