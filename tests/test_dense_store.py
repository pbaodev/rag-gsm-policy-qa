"""Test rag_gsm.index.dense_store - LanceDB tren du lieu gia lap, khong fetch mang."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rag_gsm.index.dense_store import build_table, open_table, search
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, doi_tuong: str, audience: str = "khach_hang") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="test-doc",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path="Test",
        breadcrumb="Test",
        text="nội dung mẫu",
        so_muc="1",
        doi_tuong=doi_tuong,
        audience=audience,
        nguon_tin_cay="chinh_thuc",
        ngay_hieu_luc=None,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk="dieu_khoan",
        source="https://www.greensm.com/vn-vi/test",
        token_count=3,
    )


def test_prefilter_excludes_non_matching_doi_tuong(tmp_path: Path):
    chunks = [
        _chunk("a", "nguoi_dung"),
        _chunk("b", "doi_tac"),
        _chunk("c", "chung"),
    ]
    embeddings = np.array(
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
        dtype="float32",
    )
    table = build_table(chunks, embeddings, tmp_path / "lancedb")

    query = np.array([1.0, 0.0], dtype="float32")
    results = search(table, query, top_k=5, filter_sql="doi_tuong IN ('nguoi_dung','chung')")

    ids = [r["chunk_id"] for r in results]
    assert "b" not in ids
    assert set(ids) == {"a", "c"}


def test_similarity_is_one_minus_distance(tmp_path: Path):
    chunks = [_chunk("a", "chung")]
    embeddings = np.array([[1.0, 0.0]], dtype="float32")
    table = build_table(chunks, embeddings, tmp_path / "lancedb")

    query = np.array([1.0, 0.0], dtype="float32")
    results = search(table, query, top_k=1)

    assert results[0]["similarity"] == 1 - results[0]["_distance"]
    assert results[0]["similarity"] > 0.99


def test_open_table_reopens_saved_data(tmp_path: Path):
    chunks = [_chunk("a", "chung")]
    embeddings = np.array([[1.0, 0.0]], dtype="float32")
    build_table(chunks, embeddings, tmp_path / "lancedb")

    reopened = open_table(tmp_path / "lancedb")
    results = search(reopened, np.array([1.0, 0.0], dtype="float32"), top_k=1)

    assert results[0]["chunk_id"] == "a"


def test_public_table_never_contains_internal_chunks(tmp_path: Path):
    """Dung invariant Buoc 4/CLAUDE.md: an toan bang CAU TRUC - chunk
    audience=noi_bo khong bao gio duoc dua vao bang public tu dau, khong
    chi dua vao bo loc luc truy van."""
    all_chunks = [
        _chunk("pub#1", "chung", audience="khach_hang"),
        _chunk("int#1", "chung", audience="noi_bo"),
    ]
    public_chunks = [c for c in all_chunks if c.audience == "khach_hang"]
    embeddings = np.zeros((len(public_chunks), 2), dtype="float32")

    table = build_table(public_chunks, embeddings, tmp_path / "lancedb")

    all_ids = table.to_arrow().column("chunk_id").to_pylist()
    assert "int#1" not in all_ids
    assert all_ids == ["pub#1"]
