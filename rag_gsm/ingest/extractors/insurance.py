"""Extractor cho '/vn-vi/bao-hiem-khach-hang' (Bao hiem khach hang, 1 bang).

Nguon: pageProps.insuranceData.{columns, rows}. Chi dung Markdown table o
day; viet lai tung hang thanh cau de embed/BM25 la viec cua Buoc 2
(chunk), khong phai ingest.
"""

from __future__ import annotations

import datetime as _dt

from rag_gsm.ingest.normalize import make_document, render_markdown_file
from rag_gsm.ingest.web import fetch_next_data
from rag_gsm.schemas import Document

PATH = "/vn-vi/bao-hiem-khach-hang"
SOURCE_URL = f"https://www.greensm.com{PATH}"
DOC_ID = "bao-hiem-khach-hang"


def _cell_to_str(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", " ").replace("|", "\\|").strip()


def _rows_to_markdown_table(columns: str, rows: list[dict]) -> str:
    """`columns` la mot chuoi ngan cach boi "|" (vd "Quyen loi|So tien"),
    khong phai list nhu doan dau tuong - phat hien 2026-09-22 khi bang
    hien thi toan ky tu roi. Moi hang trong `rows` la dict {value1, value2,
    ...} khop theo VI TRI voi cot da tach."""
    col_labels = columns.split("|")
    value_keys = [f"value{i + 1}" for i in range(len(col_labels))]

    header = "| " + " | ".join(col_labels) + " |"
    sep = "|" + "|".join(["---"] * len(col_labels)) + "|"
    body_lines = []
    for row in rows:
        cells = [_cell_to_str(row.get(k)) for k in value_keys]
        body_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body_lines])


def extract() -> tuple[Document, str]:
    data = fetch_next_data(PATH)
    ins = data["props"]["pageProps"]["insuranceData"]
    fetched_at = _dt.date.today().isoformat()

    table_md = _rows_to_markdown_table(ins["columns"], ins["rows"])
    body_markdown = f"# Bảo hiểm khách hàng\n\n{table_md}"

    doc = make_document(
        doc_id=DOC_ID,
        source=SOURCE_URL,
        title="Bảo hiểm khách hàng",
        doc_type="bao_hiem",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at=fetched_at,
        body_text=table_md,
        markdown_path=f"data/markdown/{DOC_ID}.md",
    )
    return doc, body_markdown


def extract_and_render() -> tuple[Document, str]:
    doc, body_md = extract()
    return doc, render_markdown_file(doc, body_md)
