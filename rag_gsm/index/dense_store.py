"""LanceDB (Buoc 4 da chot): cosine, quet phang (khong ANN o quy mo vai
tram chunk). Loc TRUOC khi xep hang - luon truyen prefilter=True tuong
minh, vi loc sau co the tra thieu hoac khong tra gi (xem CLAUDE.md)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import lancedb
import numpy as np

from rag_gsm.schemas import Chunk

VECTOR_COLUMN = "vector"
TABLE_NAME = "chunks"


def _chunk_to_row(chunk: Chunk, vector: np.ndarray) -> dict:
    row = dataclasses.asdict(chunk)
    row[VECTOR_COLUMN] = vector.astype("float32")
    row["text_embed"] = chunk.text_to_index()
    return row


def build_table(chunks: list[Chunk], embeddings: np.ndarray, db_path: Path, table_name: str = TABLE_NAME):
    db = lancedb.connect(str(db_path))
    rows = [_chunk_to_row(c, embeddings[i]) for i, c in enumerate(chunks)]
    return db.create_table(table_name, data=rows, mode="overwrite")


def open_table(db_path: Path, table_name: str = TABLE_NAME):
    db = lancedb.connect(str(db_path))
    return db.open_table(table_name)


def search(table, query_vector: np.ndarray, top_k: int, filter_sql: str | None = None) -> list[dict]:
    """`filter_sql` la mot dieu kien SQL tren cac cot phang cua bang (vd
    "doi_tuong IN ('nguoi_dung','chung') AND audience = 'khach_hang'")."""
    q = table.search(query_vector, vector_column_name=VECTOR_COLUMN).metric("cosine")
    if filter_sql:
        q = q.where(filter_sql, prefilter=True)
    rows = q.limit(top_k).to_list()
    for row in rows:
        row["similarity"] = 1 - row["_distance"]
    return rows
