"""Test _rows_to_markdown_table voi dung cau truc that cua insuranceData
(phat hien 2026-09-22: `columns` la chuoi ngan cach "|", khong phai list;
`rows` la dict {value1, value2, ...} khop theo vi tri)."""

from rag_gsm.ingest.extractors.insurance import _rows_to_markdown_table

REAL_COLUMNS = "Quyền lợi bảo hiểm|Số tiền bảo hiểm"
REAL_ROWS = [
    {"value1": "Tử vong do tai nạn trong chuyến đi", "value2": "500.000.000 VNĐ/vụ"},
    {"value1": "Trợ cấp nằm viện do tai nạn trong chuyến đi", "value2": "Lên tới 300.000 VNĐ/ngày"},
]


def test_columns_split_correctly_not_char_by_char():
    md = _rows_to_markdown_table(REAL_COLUMNS, REAL_ROWS)
    header_line = md.splitlines()[0]
    assert header_line == "| Quyền lợi bảo hiểm | Số tiền bảo hiểm |"


def test_rows_mapped_by_position():
    md = _rows_to_markdown_table(REAL_COLUMNS, REAL_ROWS)
    assert "| Tử vong do tai nạn trong chuyến đi | 500.000.000 VNĐ/vụ |" in md


def test_separator_row_matches_column_count():
    md = _rows_to_markdown_table(REAL_COLUMNS, REAL_ROWS)
    sep_line = md.splitlines()[1]
    assert sep_line == "|---|---|"
