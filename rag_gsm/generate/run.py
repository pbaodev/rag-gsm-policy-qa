"""CLI thu cong: uv run python -m rag_gsm.generate.run "cau hoi" - noi
toan bo pipeline that (index/public that, reranker that, Ollama that) de
doc ket qua tren du lieu that truoc khi co eval (Buoc 9)."""

from __future__ import annotations

import sys
from pathlib import Path

from rag_gsm.config import load_config
from rag_gsm.generate.answer import generate_answer
from rag_gsm.generate.llm_adapter import build_llm_adapter
from rag_gsm.index.bm25_store import load_bm25_index
from rag_gsm.index.build import load_all_chunks
from rag_gsm.index.dense_store import open_table
from rag_gsm.index.embedder import Bge3Embedder
from rag_gsm.retrieve.pipeline import retrieve_with_fallback
from rag_gsm.retrieve.rerank import VietnameseReranker

PUBLIC_INDEX_DIR = Path("index") / "public"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Dung: uv run python -m rag_gsm.generate.run "cau hoi"')
    query = sys.argv[1]

    config = load_config()
    chunk_lookup = {c.chunk_id: c for c in load_all_chunks() if c.audience == "khach_hang"}

    table = open_table(PUBLIC_INDEX_DIR / "lancedb")
    bm25_index = load_bm25_index(PUBLIC_INDEX_DIR / "bm25")
    embedder = Bge3Embedder(model_name=config.embedding.model)
    reranker = VietnameseReranker(model_name=config.rerank.model)
    llm = build_llm_adapter(config.generation.model, temperature=config.generation.temperature)

    retrieval = retrieve_with_fallback(
        query,
        embedder=embedder,
        table=table,
        bm25_index=bm25_index,
        chunk_lookup=chunk_lookup,
        reranker=reranker,
        llm=llm,
        config=config,
    )
    answer = generate_answer(query, retrieval, llm, chunk_lookup)

    print(f"Nhanh: {answer.branch}")
    print(f"Do tre: {retrieval.trace.latency_ms}")
    print()
    print(answer.text)
    if answer.citations:
        print()
        print("Nguon:")
        for c in answer.citations:
            print(f"  [{c.n}] {c.chunk_id} - {c.heading_path} ({c.source})")


if __name__ == "__main__":
    main()
