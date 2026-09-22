"""Test rag_gsm.eval.baseline - run_baseline() loc doi_tuong TRUOC khi
dua vao prompt (cung invariant nhu hybrid/fallback), khong qua retrieve."""

from __future__ import annotations

from rag_gsm.eval.baseline import run_baseline
from rag_gsm.schemas import Chunk


def _chunk(chunk_id: str, text: str, doi_tuong: str = "chung") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="d",
        parent_id=None,
        doc_type="dieu_khoan",
        heading_path=f"Test {chunk_id}",
        breadcrumb=f"Test {chunk_id}",
        text=text,
        so_muc="1",
        doi_tuong=doi_tuong,
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        ngay_hieu_luc=None,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk="dieu_khoan",
        source="https://www.greensm.com/vn-vi/test",
        token_count=5,
    )


class FakeLLM:
    def __init__(self, response: str):
        self.calls = 0
        self.last_user = ""
        self._response = response

    def generate(self, system, user):
        self.calls += 1
        self.last_user = user
        return self._response

    def generate_json(self, system, user, schema_hint):
        raise NotImplementedError


def test_baseline_excludes_doi_tac_chunks():
    chunks = [
        _chunk("a", "dieu khoan nguoi dung", "nguoi_dung"),
        _chunk("b", "dieu khoan doi tac", "doi_tac"),
    ]
    llm = FakeLLM("Cau tra loi [1].")

    answer = run_baseline("cau hoi", chunks, llm)

    assert "dieu khoan doi tac" not in llm.last_user
    assert "dieu khoan nguoi dung" in llm.last_user
    assert answer.branch == "baseline"
    assert llm.calls == 1


def test_baseline_builds_citations_for_all_included_chunks():
    chunks = [_chunk("a", "noi dung a"), _chunk("b", "noi dung b")]
    llm = FakeLLM("Tra loi [1] va [2].")

    answer = run_baseline("cau hoi", chunks, llm)

    assert [c.chunk_id for c in answer.citations] == ["a", "b"]
