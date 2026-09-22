"""LLM-judge (Buoc 9 da chot: Claude, temperature 0, rubric 4 tieu chi
TACH ROI) - "giam khao phai manh hon thi sinh", khong dung qwen3:4b
(model sinh cau tra loi) de tu cham chinh no."""

from __future__ import annotations

from rag_gsm.schemas import Answer, GoldenQuestion, JudgeVerdict, LLMAdapter

DEFAULT_JUDGE_MODEL = "claude-sonnet-5"

JUDGE_SYSTEM_PROMPT = (
    "Ban la giam khao danh gia cau tra loi cua mot he thong tra cuu chinh "
    "sach Green SM. Cham theo dung 4 tieu chi TACH ROI, khong tron lan:\n"
    "1. dung_noi_dung (bool): noi dung cau tra loi co dung so voi dap an "
    "mau khong, bat ke cach dien dat khac nhau.\n"
    "2. groundedness (0.0-1.0): cau tra loi co thuc su dua tren cac chunk "
    "duoc trich dan khong, hay tu bia them.\n"
    "3. citation_dung (bool): cac so [n] trong cau tra loi co tro dung "
    "chunk lien quan khong.\n"
    "4. khong_biet_dung_luc (bool): neu he thong tra loi 'khong biet', "
    "dieu do co dung luc khong (that su khong du thong tin); neu he "
    "thong TRA LOI LIEU khi dang le phai noi 'khong biet', tieu chi nay "
    "phai la false.\n"
    'Tra ve DUNG JSON: {"dung_noi_dung": bool, "groundedness": float, '
    '"citation_dung": bool, "khong_biet_dung_luc": bool, "ghi_chu": str}'
)


def _format_citations(answer: Answer) -> str:
    if not answer.citations:
        return "(khong co trich dan nao)"
    return "\n".join(f"[{c.n}] {c.chunk_id} - {c.heading_path}" for c in answer.citations)


def judge_answer(question: GoldenQuestion, answer: Answer, llm: LLMAdapter) -> JudgeVerdict:
    user_prompt = (
        f"Cau hoi: {question.cau_hoi}\n"
        f"Dap an mau: {question.gold_answer}\n"
        f"Nhanh ky vong: {question.nhanh_ky_vong}\n\n"
        f"Cau tra loi he thong sinh ra (nhanh thuc te: {answer.branch}):\n{answer.text}\n\n"
        f"Cac nguon he thong trich dan:\n{_format_citations(answer)}"
    )
    raw = llm.generate_json(
        JUDGE_SYSTEM_PROMPT,
        user_prompt,
        schema_hint=(
            '{"dung_noi_dung": bool, "groundedness": float, "citation_dung": bool, '
            '"khong_biet_dung_luc": bool, "ghi_chu": str}'
        ),
    )
    return JudgeVerdict(
        question_id=question.id,
        dung_noi_dung=bool(raw.get("dung_noi_dung", False)),
        groundedness=float(raw.get("groundedness", 0.0)),
        citation_dung=bool(raw.get("citation_dung", False)),
        khong_biet_dung_luc=bool(raw.get("khong_biet_dung_luc", False)),
        ghi_chu=raw.get("ghi_chu", ""),
    )
