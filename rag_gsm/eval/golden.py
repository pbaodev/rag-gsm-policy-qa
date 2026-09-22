"""Doc eval/golden_questions.jsonl - bo cau hoi vang (Buoc 9 da chot).
50 cau dau (2026-09-22), nguon that tu data/chunks/*.jsonl, xem CLAUDE.md."""

from __future__ import annotations

import json
from pathlib import Path

from rag_gsm.schemas import GoldenQuestion

DEFAULT_GOLDEN_PATH = Path("eval") / "golden_questions.jsonl"


def load_golden_questions(path: Path = DEFAULT_GOLDEN_PATH) -> list[GoldenQuestion]:
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            questions.append(GoldenQuestion(**json.loads(line)))
    return questions
