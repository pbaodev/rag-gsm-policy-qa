"""Test heading.py bang doan mau chep tay, phong theo cau truc that da
kiem chung ngay 2026-09-22 (xem docs/learning/01-ingestion.md)."""

from rag_gsm.ingest.heading import (
    check_numbering_continuity,
    classify_line,
    strip_inline_html,
    to_markdown,
)

# Rut gon tu generalItems[0] (Dieu khoan su dung) - giu dung khuon
# "1. TIEU DE HOA" > "1.1." > "1.1.1.", ngan dong bang \r\n nhu JSON that.
SAMPLE_DIEU_KHOAN = (
    "Cập nhật và có hiệu lực áp dụng từ ngày: 07/08/2026\r\n\r\n"
    "Chào mừng Bạn đến với GREEN SM.\r\n\r\n"
    "1. ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ\r\n\r\n"
    "1.1. Ứng Dụng là ứng dụng di động do Công ty phát triển.\r\n\r\n"
    "1.2. Nền Tảng là trang thông tin điện tử của Công ty.\r\n\r\n"
    "2. GIÁ VÀ THANH TOÁN\r\n\r\n"
    "2.1. Giá cước hiển thị trên Ứng Dụng trước khi Bạn đặt chuyến.\r\n\r\n"
    "2.1.1. Giá có thể thay đổi theo thời gian thực.\r\n\r\n"
    "2.2. Phương thức thanh toán bao gồm tiền mặt và ví điện tử.\r\n\r\n"
    "3. HIỆU LỰC\r\n\r\n"
    "3.1. Điều khoản có hiệu lực kể từ ngày đăng ký.\r\n"
)

# Tieu de bat dau bang chu so - phai van duoc nhan la heading cap 1.
SAMPLE_TITLE_STARTS_WITH_DIGIT = "5. 24/7 hỗ trợ khách hàng\r\n\r\nNội dung.\r\n"

# Truong hop nhay so (gia lap loi OCR) - dung de test canh bao.
SAMPLE_SKIPPED_NUMBER = "1. MỘT\r\n\r\nNội dung 1.\r\n\r\n3. BA\r\n\r\nNội dung 3.\r\n"

# That, tu generalItems[2] (Phu luc 2 - Quy che Car): tieu de boc trong
# <strong>, khac voi Dieu khoan su dung dung dong so tran khong the.
SAMPLE_HTML_WRAPPED_HEADING = (
    "PHỤ LỤC 2 – QUY CHẾ SỬ DỤNG SẢN PHẨM GREEN SM CAR\r\n\r\n"
    "<i>(Phụ lục Quy chế này đính kèm và là một phần của Điều khoản sử dụng)</i>\r\n\r\n"
    "<strong>1. Quy định chung</strong>\r\n\r\n"
    "Ứng dụng cho phép Bạn tìm kiếm và kết nối với Đối tác vận chuyển bằng xe ô tô.\r\n\r\n"
    "<strong>2. Quy trình cung cấp Sản Phẩm </strong>\r\n\r\n"
    "Bước 1: Bật chế độ trực tuyến khi sẵn sàng được kết nối với Người dùng\r\n"
)


def test_classify_line_level1():
    hl = classify_line("1. ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ")
    assert hl.level == 1
    assert hl.so_muc == "1"
    assert hl.text == "ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ"


def test_classify_line_level2():
    hl = classify_line("1.1. Ứng Dụng là ứng dụng di động.")
    assert hl.level == 2
    assert hl.so_muc == "1.1"


def test_classify_line_level3():
    hl = classify_line("2.1.1. Giá có thể thay đổi theo thời gian thực.")
    assert hl.level == 3
    assert hl.so_muc == "2.1.1"


def test_classify_line_level0_body_text():
    hl = classify_line("Chào mừng Bạn đến với GREEN SM.")
    assert hl.level == 0


def test_title_starting_with_digit_is_still_level1():
    """Bug da sua: (?!\\d) tung loai nham tieu de bat dau bang so."""
    md = to_markdown(SAMPLE_TITLE_STARTS_WITH_DIGIT)
    assert "# 5. 24/7 hỗ trợ khách hàng" in md


def test_to_markdown_produces_correct_heading_levels():
    md = to_markdown(SAMPLE_DIEU_KHOAN)
    assert "# 1. ĐỊNH NGHĨA VÀ GIẢI THÍCH TỪ NGỮ" in md
    assert "## 1.1. Ứng Dụng là ứng dụng di động do Công ty phát triển." in md
    assert "### 2.1.1. Giá có thể thay đổi theo thời gian thực." in md
    assert "# 2. GIÁ VÀ THANH TOÁN" in md
    assert "# 3. HIỆU LỰC" in md


def test_to_markdown_keeps_body_text_untouched():
    md = to_markdown(SAMPLE_DIEU_KHOAN)
    assert "Chào mừng Bạn đến với GREEN SM." in md


def test_numbering_continuity_ok():
    assert check_numbering_continuity(SAMPLE_DIEU_KHOAN) == []


def test_numbering_continuity_detects_gap():
    warnings = check_numbering_continuity(SAMPLE_SKIPPED_NUMBER)
    assert len(warnings) == 1
    assert "[1, 3]" in warnings[0]


def test_strip_inline_html():
    assert strip_inline_html("<strong>1. Quy định chung</strong>") == "1. Quy định chung"
    assert strip_inline_html("không có thẻ nào") == "không có thẻ nào"


def test_strip_inline_html_converts_anchor_to_markdown_link():
    raw = (
        'Xem thêm tại <a href="https://www.greensm.com/vn-vi/bao-hiem-khach-hang" '
        'style="color: #28bdbf;" target="_blank">Bảo hiểm khách hàng</a> để biết chi tiết.'
    )
    result = strip_inline_html(raw)
    assert result == (
        "Xem thêm tại [Bảo hiểm khách hàng]"
        "(https://www.greensm.com/vn-vi/bao-hiem-khach-hang) để biết chi tiết."
    )


def test_html_wrapped_heading_still_detected():
    """Bug that tim thay 2026-09-22: <strong> boc tieu de lam mat heading
    cua Phu luc 2 (chi con thay muc 3.1 tro di, mat het muc 1 va 2)."""
    md = to_markdown(SAMPLE_HTML_WRAPPED_HEADING)
    assert "# 1. Quy định chung" in md
    assert "# 2. Quy trình cung cấp Sản Phẩm" in md
    assert "<strong>" not in md
    assert "<i>" not in md


def test_classify_line_strips_html_when_called_directly():
    hl = classify_line("<strong>1. Quy định chung</strong>")
    assert hl.level == 1
    assert hl.so_muc == "1"
    assert hl.text == "Quy định chung"
