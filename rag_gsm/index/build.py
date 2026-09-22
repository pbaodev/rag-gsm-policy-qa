"""Dung lai toan bo index/{public,internal}/{lancedb,bm25}/ tu data/chunks/*.jsonl.

Tach thu muc theo `audience` (khach_hang -> public, noi_bo -> internal) -
an toan bang CAU TRUC, khong chi bang bo loc (xem CLAUDE.md invariant
"Isolation by structure, not just by filter").
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_gsm.config import load_config
from rag_gsm.index.bm25_store import build_bm25_index, save_bm25_index
from rag_gsm.index.dense_store import build_table
from rag_gsm.index.embedder import Bge3Embedder
from rag_gsm.schemas import Chunk

CHUNKS_DIR = Path("data/chunks")
INDEX_DIR = Path("index")

_AUDIENCE_TO_DIR = {"khach_hang": "public", "noi_bo": "internal"}


def load_all_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(CHUNKS_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chunks.append(Chunk(**json.loads(line)))
    return chunks


def build_index_for_audience(chunks: list[Chunk], embedder: Bge3Embedder, out_dir: Path, k1: float, b: float) -> None:
    texts = [c.text_to_index() for c in chunks]
    embeddings = embedder.embed_documents(texts)

    build_table(chunks, embeddings, out_dir / "lancedb")

    bm25 = build_bm25_index(texts, k1=k1, b=b)
    save_bm25_index(bm25, [c.chunk_id for c in chunks], out_dir / "bm25")


def main() -> None:
    chunks = load_all_chunks()
    if not chunks:
        raise SystemExit(f"Khong tim thay chunk nao trong {CHUNKS_DIR} - chay chunk truoc.")

    config = load_config()
    embedder = Bge3Embedder(model_name=config.embedding.model)

    by_audience: dict[str, list[Chunk]] = {}
    for c in chunks:
        by_audience.setdefault(c.audience, []).append(c)

    for audience, group in by_audience.items():
        dir_name = _AUDIENCE_TO_DIR.get(audience)
        if dir_name is None:
            raise ValueError(f"audience '{audience}' chua co thu muc index tuong ung")
        out_dir = INDEX_DIR / dir_name
        build_index_for_audience(group, embedder, out_dir, config.bm25.k1, config.bm25.b)
        print(f"{dir_name}: {len(group)} chunk -> {out_dir}/{{lancedb,bm25}}")

    print(f"\nTong: {len(chunks)} chunk, model embedding: {config.embedding.model}")


if __name__ == "__main__":
    main()
