"""Embedder (Protocol tu schemas.py) bang bge-m3 qua sentence-transformers
(Buoc 3 da chot: local, MPS, khong can prefix cho bge-m3)."""

from __future__ import annotations

import numpy as np


class Bge3Embedder:
    """bge-m3 khong can prefix rieng cho cau hoi/tai lieu (khac e5, Qwen3) -
    xem docs/learning/03-embedding.md."""

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        if device is None:
            import torch

            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._model = SentenceTransformer(model_name, device=device)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    def embed_query(self, text: str) -> np.ndarray:
        return self._model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
