"""Extractor cho '/vn-vi/terms-policies/e-green-wallet-payment-terms'
(Dieu khoan thanh toan bang The/Vi E-Green).

Bug that tim lai duoc 2026-09-23: URL cu ghi trong 01-ingestion.md
("/e-green-wallet-payment-terms") la 404; URL dung theo dung khuon
"/vn-vi/terms-policies/<slug>" nhu cac trang khac (general, privacy-notice,
service-agreement) - chua tim ra truoc day vi thu sai khuon URL, khong
phai vi trang thuc su bien mat.

Cau truc JSON KHAC voi service-agreement (dung serviceItems[] danh sach) -
trang nay dung serviceExcerpt (MOT chuoi HTML + \\r\\n dai, serviceItems
la null), giong khuon tung phan tu generalItems[] hon (tieu de
<strong>N. ...</strong>, than van ban ngan dong bang \\r\\n) - vi du nua
cho bai hoc "khong doan hinh dang JSON tu mot lan xem truoc" (xem
insuranceData.columns o Ingest gotchas, CLAUDE.md).
"""

from __future__ import annotations

import datetime as _dt

from rag_gsm.ingest import heading
from rag_gsm.ingest.normalize import make_document
from rag_gsm.ingest.web import fetch_next_data
from rag_gsm.schemas import Document

PATH = "/vn-vi/terms-policies/e-green-wallet-payment-terms"
SOURCE_URL = f"https://www.greensm.com{PATH}"
DOC_ID = "dieu-khoan-vi-e-green"


def _clean_title(raw_title: str) -> str:
    return " ".join(raw_title.replace("\r\n", " ").split())


def extract() -> tuple[Document, str]:
    """Fetch va tra ve (Document, than Markdown)."""
    data = fetch_next_data(PATH)
    service_data = data["props"]["pageProps"]["serviceData"]
    body_text = service_data["serviceExcerpt"]
    body_md = heading.to_markdown(body_text)
    doc = make_document(
        doc_id=DOC_ID,
        source=SOURCE_URL,
        title=_clean_title(service_data["serviceTitle"]),
        doc_type="dieu_khoan",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at=_dt.date.today().isoformat(),
        body_text=body_text,
        markdown_path=f"data/markdown/{DOC_ID}.md",
    )
    return doc, body_md
