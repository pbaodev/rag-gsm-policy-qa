"""Cac dataclass/interface dung chung giua cac module.

Xem docs/kien-truc-code.md de biet ly do cua tung field. Ten field giu dung
nhu da chot trong docs/learning/ (khong dat lai ten).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np


@dataclass
class Document:
    """Dau ra ingest, dau vao chunk - front matter Buoc 1."""

    doc_id: str
    source: str
    title: str
    doc_type: str  # faq | dieu_khoan | chinh_sach | quy_che | bao_hiem
    audience: str  # khach_hang | noi_bo
    nguon_tin_cay: str  # chinh_thuc | bao_chi | cong_dong | noi_bo
    fetched_at: str
    content_hash: str
    ngay_hieu_luc: str | None
    markdown_path: str


@dataclass
class Chunk:
    """Dau ra chunk, dau vao index - metadata Buoc 2."""

    chunk_id: str  # "general#3.2", "faq#3.6"
    doc_id: str
    parent_id: str | None
    doc_type: str
    heading_path: str
    breadcrumb: str  # "Van ban > muc > khoan" - dung cho embed, BM25, outline fallback
    text: str  # noi dung chunk, KHONG kem breadcrumb
    so_muc: str | None
    doi_tuong: str  # nguoi_dung | doi_tac | chung
    audience: str
    nguon_tin_cay: str
    ngay_hieu_luc: str | None
    trang_bat_dau: int | None
    trang_ket_thuc: int | None
    loai_chunk: str  # faq | dieu_khoan | bang | generic
    source: str
    token_count: int

    def text_to_index(self) -> str:
        return f"{self.breadcrumb}\n{self.text}"  # breadcrumb dung dau (Buoc 2)


class Embedder(Protocol):
    """Buoc 3 - giau prefix/instruction rieng tung model."""

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


@dataclass
class RetrievalCandidate:
    """Mot chunk qua cac tang diem - de trace panel (Buoc 8)."""

    chunk_id: str
    dense_score: float | None = None
    dense_rank: int | None = None
    bm25_score: float | None = None
    bm25_rank: int | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None  # da sigmoid, 0-1 (Buoc 5)


@dataclass
class TraceInfo:
    """Toan bo du lieu noi bo mot luot truy van (Buoc 8)."""

    branch: Literal["hybrid", "pageindex_fallback", "khong_biet"]
    candidates_before_rerank: list[RetrievalCandidate] = field(default_factory=list)
    candidates_after_rerank: list[RetrievalCandidate] = field(default_factory=list)
    threshold: float = 0.0
    fallback_outline_size: int | None = None
    fallback_node_list: list[dict] | None = None  # [{chunk_id, trich_dan}] - Buoc 6
    citation_map: dict[int, str] = field(default_factory=dict)  # n -> chunk_id
    latency_ms: dict[str, float] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Dau ra Buoc 5/6, dau vao Buoc 7."""

    branch: str
    chunks: list[Chunk]  # da reorder (sandwich), toi da K=3
    trace: TraceInfo


@dataclass
class Citation:
    n: int
    chunk_id: str
    source: str
    heading_path: str
    trang: int | None = None


@dataclass
class Answer:
    """Dau ra Buoc 7, dau vao UI + eval."""

    text: str  # co [n] inline
    citations: list[Citation]
    branch: str


class LLMAdapter(Protocol):
    """Buoc 0 adapter mong - Ollama dev, Claude khi can chat luong."""

    def generate(self, system: str, user: str) -> str: ...

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict: ...


@dataclass
class GoldenQuestion:
    """Buoc 9."""

    id: str
    cau_hoi: str
    chu_de: str
    do_kho: str
    nhanh_ky_vong: str  # hybrid | pageindex_fallback | khong_biet
    gold_chunk_ids: list[str]
    gold_answer: str
    ghi_chu: str = ""


@dataclass
class JudgeVerdict:
    """Buoc 9 - rubric 4 tieu chi tach roi."""

    question_id: str
    dung_noi_dung: bool
    groundedness: float  # 0-1
    citation_dung: bool
    khong_biet_dung_luc: bool
    ghi_chu: str = ""
