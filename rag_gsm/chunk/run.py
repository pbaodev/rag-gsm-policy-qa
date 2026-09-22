"""Chay chunk tren toan bo data/markdown/*.md, ghi data/chunks/<doc_id>.jsonl.

Doc lai output cua ingest (khong fetch mang) - data/markdown/ la nguon that
cho chunk (xem CLAUDE.md "Data layout").
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from rag_gsm.chunk.loader import load_document
from rag_gsm.chunk.rules import BUDGET_TOKENS, chunk_document
from rag_gsm.schemas import Chunk

MARKDOWN_DIR = Path("data/markdown")
CHUNKS_DIR = Path("data/chunks")


def _write_jsonl(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(dataclasses.asdict(chunk), ensure_ascii=False) + "\n")


def main() -> None:
    md_files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        raise SystemExit(f"Khong tim thay file .md nao trong {MARKDOWN_DIR} - chay ingest truoc.")

    total_chunks = 0
    label_counts: dict[str, int] = {}
    oversized: list[str] = []

    for md_path in md_files:
        doc, body = load_document(md_path)
        chunks = chunk_document(doc, body)
        _write_jsonl(chunks, CHUNKS_DIR / f"{doc.doc_id}.jsonl")

        for c in chunks:
            label_counts[c.doi_tuong] = label_counts.get(c.doi_tuong, 0) + 1
            if c.token_count > BUDGET_TOKENS:
                oversized.append(f"{c.chunk_id} ({c.token_count} token)")
        total_chunks += len(chunks)
        print(f"{doc.doc_id}: {len(chunks)} chunk")

    print(f"\nTong: {total_chunks} chunk tu {len(md_files)} tai lieu")
    print(f"doi_tuong: {label_counts}")
    if oversized:
        print(f"Van vuot ngan sach ({BUDGET_TOKENS} token) sau khi tach het co the: {oversized}")


if __name__ == "__main__":
    main()
