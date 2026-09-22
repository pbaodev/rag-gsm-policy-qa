"""Test rag_gsm.chunk.rules - dung fixture chep tay, khong fetch mang.

Cac test nay bam theo dung 2 bug thuc te tim thay khi chay chunk tren
data/markdown/*.md that (2026-09-22):
1. Khoan khac doi_tuong lien tiep (vd Dieu 4 cua phu-luc-02-quy-che-car)
   phai tach rieng, ke ca khi gop lai van vua ngan sach.
2. Tai lieu khong co heading nao (vd phu-luc-01/13/15) khong duoc gan
   doi_tuong theo tung doan van - se xe vun mot mach van xuoi lien tuc.
"""

from __future__ import annotations

from rag_gsm.chunk.rules import (
    chunk_bao_hiem,
    chunk_dieu_khoan,
    chunk_faq,
    label_doi_tuong,
)
from rag_gsm.schemas import Document


def _doc(doc_type: str, doc_id: str = "test-doc") -> Document:
    return Document(
        doc_id=doc_id,
        source="https://www.greensm.com/vn-vi/test",
        title="Tài liệu kiểm thử",
        doc_type=doc_type,
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at="2026-09-22",
        content_hash="deadbeef",
        ngay_hieu_luc=None,
        markdown_path=f"data/markdown/{doc_id}.md",
    )


def test_label_doi_tuong_nguoi_dung_only():
    assert label_doi_tuong("Người dùng phải tuân thủ quy định pháp luật.") == "nguoi_dung"


def test_label_doi_tuong_doi_tac_only():
    assert label_doi_tuong("Đối tác phải tuân thủ quy định pháp luật.") == "doi_tac"


def test_label_doi_tuong_neither_or_both_is_chung():
    assert label_doi_tuong("Green SM phải tuân thủ quy định pháp luật.") == "chung"
    assert label_doi_tuong("Người dùng và Đối tác cùng thực hiện nghĩa vụ.") == "chung"


def test_mixed_doi_tuong_never_merged_even_though_small_enough_to_fit():
    """Nguyen ban Dieu 4, phu-luc-02-quy-che-car.md - 3 khoan cong lai chi
    ~90 token (vua ngan sach thua thai) nhung PHAI tach rieng vi khac
    doi_tuong - dung invariant o CLAUDE.md, khong phai chuyen toi uu kich
    thuoc."""
    body = """# 4. Quyền và nghĩa vụ của các bên

## 4.1. Người dùng phải tuân thủ quy định pháp luật, Điều khoản, Hợp Đồng, và Chính sách Green SM khi sử dụng Dịch vụ và Sản Phẩm;

## 4.2. Đối tác phải tuân thủ quy định pháp luật, Điều khoản, Hợp Đồng, và Chính sách Green SM khi sử dụng Dịch vụ và cung cấp Sản Phẩm;

## 4.3. Green SM phải tuân thủ quy định pháp luật, Điều khoản và Hợp Đồng."""

    chunks = chunk_dieu_khoan(_doc("dieu_khoan"), body)

    assert len(chunks) == 3
    assert [c.doi_tuong for c in chunks] == ["nguoi_dung", "doi_tac", "chung"]
    assert [c.chunk_id for c in chunks] == ["test-doc#4.1", "test-doc#4.2", "test-doc#4.3"]
    assert all(c.parent_id == "test-doc#4" for c in chunks)


def test_same_label_whole_h1_collapses_to_one_chunk():
    body = """# 1. Quy định chung

## 1.1. Nguyên tắc áp dụng chung cho mọi bên tham gia.

## 1.2. Không phân biệt đối xử giữa các bên."""

    chunks = chunk_dieu_khoan(_doc("dieu_khoan"), body)

    assert len(chunks) == 1
    assert chunks[0].doi_tuong == "chung"


def test_headingless_document_not_fragmented_by_paragraph_doi_tuong():
    """Nhai lai cau truc that cua phu-luc-01-quy-trinh-nguoi-dung.md: van
    ban khong co heading nao, xen ke nhac "Nguoi dung"/"Doi tac" qua tung
    cau trong 1 quy trinh lien tuc - truoc khi sua bug nay ra 34 chunk
    (co chunk 2 token); phai gom lai theo kich thuoc, khong ngat theo nhan."""
    body = """Phần B – Các điều khoản bổ sung

Phụ lục 1: QUY TRÌNH DÀNH CHO NGƯỜI DÙNG

Bước 1: Người dùng tải và cài đặt Ứng dụng.

Bước 2: Đối tác xác nhận lệnh nhận chuyến đi từ Ứng dụng."""

    chunks = chunk_dieu_khoan(_doc("dieu_khoan"), body)

    assert len(chunks) == 1
    assert chunks[0].parent_id is None


def test_faq_one_question_is_one_chunk():
    body = """# 1. An toàn

## 1.1. Tôi gặp tai nạn thì làm gì?

Bạn hãy bình tĩnh và gọi 115 nếu cần cấp cứu."""

    chunks = chunk_faq(_doc("faq"), body)

    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == "test-doc#1.1"
    assert c.doi_tuong == "nguoi_dung"
    assert c.loai_chunk == "faq"
    assert "Tôi gặp tai nạn thì làm gì?" in c.text
    assert "gọi 115" in c.text


def test_faq_oversized_answer_splits_and_stays_under_budget():
    long_answer = "\n\n".join(
        f"Đây là đoạn văn số {i} trong một câu trả lời rất dài, "
        "được viết ra chỉ để kiểm tra việc tách chunk khi vượt ngân sách "
        "token quy định cho một cặp hỏi đáp trong hệ thống câu hỏi thường gặp."
        for i in range(1, 40)
    )
    body = f"""# 1. An toàn

## 1.1. Câu hỏi có câu trả lời rất dài

{long_answer}"""

    chunks = chunk_faq(_doc("faq"), body)

    assert len(chunks) >= 2
    assert all(c.token_count <= 500 for c in chunks)
    assert chunks[0].chunk_id == "test-doc#1.1-a"
    assert chunks[1].chunk_id == "test-doc#1.1-b"


def test_insurance_table_is_one_chunk_with_row_sentences():
    body = """# Bảo hiểm khách hàng

| Quyền lợi bảo hiểm | Số tiền bảo hiểm |
|---|---|
| Tử vong do tai nạn trong chuyến đi | 500.000.000 VNĐ/vụ |
| Trợ cấp nằm viện do tai nạn | 300.000 VNĐ/ngày |"""

    chunks = chunk_bao_hiem(_doc("bao_hiem"), body)

    assert len(chunks) == 1
    c = chunks[0]
    assert c.loai_chunk == "bang"
    assert c.doi_tuong == "chung"
    assert "| Tử vong do tai nạn trong chuyến đi | 500.000.000 VNĐ/vụ |" in c.text
    assert "Quyền lợi bảo hiểm: Tử vong do tai nạn trong chuyến đi; Số tiền bảo hiểm: 500.000.000 VNĐ/vụ." in c.text
