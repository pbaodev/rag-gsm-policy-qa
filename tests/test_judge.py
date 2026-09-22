"""Test rag_gsm.eval.judge - judge_answer() voi LLM gia (khong goi Claude
that trong test - can ANTHROPIC_API_KEY, xem rag_gsm/eval/run.py)."""

from __future__ import annotations

from rag_gsm.eval.judge import judge_answer
from rag_gsm.schemas import Answer, Citation, GoldenQuestion


def _question() -> GoldenQuestion:
    return GoldenQuestion(
        id="q1",
        cau_hoi="huy chuyen co mat phi khong",
        chu_de="huy_chuyen",
        do_kho="dien_dat_lai",
        nhanh_ky_vong="hybrid",
        gold_chunk_ids=["faq#3.6"],
        gold_answer="mien phi trong 2 phut dau",
    )


class FakeLLM:
    def __init__(self, response: dict):
        self._response = response

    def generate(self, system, user):
        raise NotImplementedError

    def generate_json(self, system, user, schema_hint):
        return self._response


def test_judge_answer_parses_all_four_criteria():
    answer = Answer(
        text="Mien phi trong 2 phut dau [1].",
        citations=[Citation(n=1, chunk_id="faq#3.6", source="https://x", heading_path="FAQ 3.6")],
        branch="hybrid",
    )
    llm = FakeLLM(
        {"dung_noi_dung": True, "groundedness": 0.9, "citation_dung": True, "khong_biet_dung_luc": True, "ghi_chu": "tot"}
    )

    verdict = judge_answer(_question(), answer, llm)

    assert verdict.question_id == "q1"
    assert verdict.dung_noi_dung is True
    assert verdict.groundedness == 0.9
    assert verdict.citation_dung is True
    assert verdict.khong_biet_dung_luc is True


def test_judge_answer_missing_fields_default_safely():
    answer = Answer(text="...", citations=[], branch="khong_biet")
    llm = FakeLLM({})

    verdict = judge_answer(_question(), answer, llm)

    assert verdict.dung_noi_dung is False
    assert verdict.groundedness == 0.0
    assert verdict.citation_dung is False
    assert verdict.khong_biet_dung_luc is False
