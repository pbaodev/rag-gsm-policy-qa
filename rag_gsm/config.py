"""Doc config/default.toml - tat ca tham so "cho eval" nam o day, khong
hard-code trong code (xem docs/kien-truc-code.md)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config/default.toml")


@dataclass
class EmbeddingConfig:
    model: str


@dataclass
class Bm25Config:
    k1: float
    b: float


@dataclass
class RrfConfig:
    k: int
    top_n_per_branch: int


@dataclass
class RerankConfig:
    model: str
    top_k_into_rerank: int


@dataclass
class ContextConfig:
    final_k: int
    reorder: bool


@dataclass
class FallbackConfig:
    model: str
    excerpt_chars: int


@dataclass
class GenerationConfig:
    model: str
    temperature: float


@dataclass
class ThresholdsConfig:
    rerank_pass: float


@dataclass
class Config:
    embedding: EmbeddingConfig
    bm25: Bm25Config
    rrf: RrfConfig
    rerank: RerankConfig
    context: ContextConfig
    fallback: FallbackConfig
    generation: GenerationConfig
    thresholds: ThresholdsConfig


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return Config(
        embedding=EmbeddingConfig(**raw["embedding"]),
        bm25=Bm25Config(**raw["bm25"]),
        rrf=RrfConfig(**raw["rrf"]),
        rerank=RerankConfig(**raw["rerank"]),
        context=ContextConfig(**raw["context"]),
        fallback=FallbackConfig(**raw["fallback"]),
        generation=GenerationConfig(**raw["generation"]),
        thresholds=ThresholdsConfig(**raw["thresholds"]),
    )
