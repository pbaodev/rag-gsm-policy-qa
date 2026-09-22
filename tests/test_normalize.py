from rag_gsm.ingest.normalize import (
    compute_content_hash,
    extract_ngay_hieu_luc,
    make_document,
    normalize_nfc,
    render_markdown_file,
)


def test_normalize_nfc_merges_combining_marks():
    # "ệ" co the o dang NFC (1 ky tu dung san, ệ) hoac NFD (e + dau mu
    # ̂ + dau nang ̣ roi rac) - ca hai phai chuan hoa ve cung mot
    # dang, khong thi BM25/so khop chuoi se truot nhau (bai hoc Buoc 1).
    composed = normalize_nfc("Nghệ thuật")  # "Nghệ thuật" go san (NFC)
    decomposed = normalize_nfc("Nghệ thuật")  # e + dau nang + dau mu roi (NFD)
    assert composed == decomposed


def test_content_hash_stable_across_runs():
    text = "Nội dung không đổi."
    assert compute_content_hash(text) == compute_content_hash(text)


def test_content_hash_changes_with_content():
    assert compute_content_hash("A") != compute_content_hash("B")


def test_extract_ngay_hieu_luc_from_json_description_style():
    text = "Cập nhật và có hiệu lực áp dụng từ ngày: 07/08/2026\r\n\r\nChào mừng Bạn."
    assert extract_ngay_hieu_luc(text) == "07/08/2026"


def test_extract_ngay_hieu_luc_alternate_phrasing():
    text = "Chính sách này có hiệu lực kể từ ngày 31/07/2026 và thay thế bản cũ."
    assert extract_ngay_hieu_luc(text) == "31/07/2026"


def test_extract_ngay_hieu_luc_none_when_absent():
    assert extract_ngay_hieu_luc("Không có ngày nào ở đây.") is None


def test_make_document_and_render_markdown_roundtrip():
    doc = make_document(
        doc_id="dieu-khoan-su-dung",
        source="https://www.greensm.com/vn-vi/terms-policies/general",
        title="Điều khoản sử dụng",
        doc_type="dieu_khoan",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at="2026-09-22",
        body_text="Có hiệu lực áp dụng từ ngày: 07/08/2026\r\n\r\n1. ĐỊNH NGHĨA",
        markdown_path="data/markdown/dieu-khoan-su-dung.md",
    )
    assert doc.ngay_hieu_luc == "07/08/2026"
    assert len(doc.content_hash) == 64  # sha256 hex

    rendered = render_markdown_file(doc, "# 1. ĐỊNH NGHĨA\n\nNội dung.")
    assert rendered.startswith("---\n")
    assert "doc_type: dieu_khoan" in rendered
    assert "ngay_hieu_luc: 07/08/2026" in rendered
    assert "# 1. ĐỊNH NGHĨA" in rendered


def test_render_markdown_file_null_ngay_hieu_luc():
    doc = make_document(
        doc_id="x",
        source="https://example.com",
        title="X",
        doc_type="dieu_khoan",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at="2026-09-22",
        body_text="Không có ngày hiệu lực ở đây.",
        markdown_path="data/markdown/x.md",
    )
    rendered = render_markdown_file(doc, "nội dung")
    assert "ngay_hieu_luc: null" in rendered
