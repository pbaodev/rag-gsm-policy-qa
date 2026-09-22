"""CrossEncoder cho rerank (Buoc 5 da chot AITeamVN/Vietnamese_Reranker,
sigmoid hoa diem tho de co thang so sanh duoc, dung lam nguong fallback).

**Sua 2026-09-22, khac tai lieu du kien:** 05-retrieval.md du kien dung
`sentence_transformers.CrossEncoder` (khong them dependency, cung mot ho
`AutoModelForSequenceClassification` nhu bge-reranker-v2-m3) - nhung
ngay chinh muc "Rui ro" cua tai lieu do da ghi "Chua xac nhan
CrossEncoder tai thang duoc AITeamVN/Vietnamese_Reranker khong loi", va
kiem chung that thi loi that:

- Repo AITeamVN/Vietnamese_Reranker chi co `sentencepiece.bpe.model` tho,
  KHONG co san `tokenizer.json` (khac bge-reranker-v2-m3, co ca hai).
- transformers 5.17.0 (dang pin, vi sentence-transformers 6.1.0 doi hoi
  transformers>=5,<6) doan nham file sentencepiece do la dinh dang
  tiktoken khi tu chuyen doi, loi ngay ca khi da cai `sentencepiece` va
  `tiktoken`.
- Ha transformers xuong <5 se lam sentence-transformers 6.1.0 khong cai
  duoc (xung dot version) - khong the sua bang cach doi phien ban chinh.

Cach sua: dung MOT MOI TRUONG TAM (`uv run --with "transformers<5"`,
khong dam vao dependency chinh) de convert tokenizer sang dinh dang fast
(`tokenizer.json`) dung 1 lan, cache theo may tai
`~/.cache/rag_gsm/tokenizer_fix/`; nap lai binh thuong tren
transformers 5.17.0 sau do khong loi. Vi vay dung thang
`AutoModelForSequenceClassification` (khong qua `CrossEncoder`) de tu
kiem soat tokenizer nao duoc nap.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from rag_gsm.schemas import Chunk, RetrievalCandidate

_TOKENIZER_CACHE_DIR = Path.home() / ".cache" / "rag_gsm" / "tokenizer_fix"
_REPAIR_SCRIPT = Path(__file__).with_name("_tokenizer_repair_script.py")
MAX_LENGTH = 2304  # AITeamVN/Vietnamese_Reranker: 256 cau hoi + 2048 van ban


def _ensure_fixed_tokenizer(model_name: str) -> Path:
    out_dir = _TOKENIZER_CACHE_DIR / model_name.replace("/", "__")
    if (out_dir / "tokenizer.json").exists():
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "uv", "run", "--with", "transformers<5", "--with", "protobuf",
            "python", str(_REPAIR_SCRIPT), model_name, str(out_dir),
        ],
        check=True,
    )
    return out_dir


class VietnameseReranker:
    def __init__(self, model_name: str = "AITeamVN/Vietnamese_Reranker", device: str | None = None) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._torch = torch
        self._device = device

        fixed_tokenizer_dir = _ensure_fixed_tokenizer(model_name)
        self._tokenizer = AutoTokenizer.from_pretrained(fixed_tokenizer_dir)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device).eval()

    def score(self, query: str, texts: list[str]) -> np.ndarray:
        inputs = self._tokenizer(
            [query] * len(texts), texts, padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"
        ).to(self._device)
        with self._torch.no_grad():
            logits = self._model(**inputs).logits.squeeze(-1)
        return self._torch.sigmoid(logits).cpu().numpy()


def rerank(
    query: str,
    candidates: list[RetrievalCandidate],
    chunk_lookup: dict[str, Chunk],
    reranker: VietnameseReranker,
    *,
    top_k_into_rerank: int = 10,
) -> list[RetrievalCandidate]:
    top = candidates[:top_k_into_rerank]
    if not top:
        return []
    texts = [chunk_lookup[c.chunk_id].text_to_index() for c in top]
    scores = reranker.score(query, texts)
    for c, s in zip(top, scores):
        c.rerank_score = float(s)
    return sorted(top, key=lambda c: c.rerank_score, reverse=True)
