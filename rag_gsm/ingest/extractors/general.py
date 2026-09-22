"""Extractor cho '/vn-vi/terms-policies/general' (Dieu khoan su dung + 15 Phu luc).

Nguon: pageProps.generalTerms.generalItems[] trong __NEXT_DATA__ - moi phan
tu la mot van ban day du, khong phai bo trich DOM. Xem
docs/learning/01-ingestion.md (sua 2026-09-22).

generalItems[12] (Chinh sach bao ve du lieu ca nhan) bi BO QUA o day vi
trung noi dung voi trang /terms-policies/privacy-notice rieng (da tach
san 14 muc co tieu de - xem privacy.py); dung ban do de tranh index
trung 2 lan.
"""

from __future__ import annotations

import datetime as _dt

from rag_gsm.ingest import heading
from rag_gsm.ingest.normalize import make_document, render_markdown_file
from rag_gsm.ingest.web import fetch_next_data
from rag_gsm.schemas import Document

PATH = "/vn-vi/terms-policies/general"
SOURCE_URL = f"https://www.greensm.com{PATH}"

# Chi so generalItems -> doc_id. Danh sach ma theo chinh so "PHU LUC N" ma
# van ban tu ghi (index i ung voi "Phu luc i", i = 1..15); index 12 bo qua.
_DOC_IDS: dict[int, str] = {
    0: "dieu-khoan-su-dung",
    1: "phu-luc-01-quy-trinh-nguoi-dung",
    2: "phu-luc-02-quy-che-car",
    3: "phu-luc-03-quy-che-bike",
    4: "phu-luc-04-quy-che-express",
    5: "phu-luc-05-quy-che-food",
    6: "phu-luc-06-khuyen-mai-truc-tuyen",
    7: "phu-luc-07-cho-thue-xe",
    8: "phu-luc-08-van-tai-tra-sau",
    9: "phu-luc-09-van-tai-tra-truoc",
    10: "phu-luc-10-quy-che-delivery",
    11: "phu-luc-11-cookies",
    # 12: bo qua - trung noi dung voi privacy-notice
    13: "phu-luc-13-mien-tru-trach-nhiem",
    14: "phu-luc-14-tai-khoan-gia-dinh",
    15: "phu-luc-15-giai-quyet-khieu-nai",
}

SKIP_INDEX = 12


def _clean_title(raw_title: str) -> str:
    return " ".join(raw_title.replace("\r\n", " ").split())


def extract() -> list[tuple[Document, str]]:
    """Fetch va tra ve danh sach (Document, than Markdown) cho tung van ban."""
    data = fetch_next_data(PATH)
    items = data["props"]["pageProps"]["generalTerms"]["generalItems"]
    fetched_at = _dt.date.today().isoformat()

    results: list[tuple[Document, str]] = []
    for i, item in enumerate(items):
        if i == SKIP_INDEX:
            continue
        doc_id = _DOC_IDS.get(i)
        if doc_id is None:
            # generalItems co them phan tu moi ma chua duoc anh xa - dieu nay
            # co nghia trang da doi cau truc, can xem lai thay vi im lang bo qua.
            raise ValueError(
                f"generalItems[{i}] chua co doc_id trong _DOC_IDS - "
                "site co the da doi cau truc, xem lai truoc khi ingest tiep."
            )
        title = _clean_title(item["title"])
        body_md = heading.to_markdown(item["description"])
        doc = make_document(
            doc_id=doc_id,
            source=SOURCE_URL,
            title=title,
            doc_type="dieu_khoan",
            audience="khach_hang",
            nguon_tin_cay="chinh_thuc",
            fetched_at=fetched_at,
            body_text=item["description"],
            markdown_path=f"data/markdown/{doc_id}.md",
        )
        results.append((doc, body_md))
    return results


def extract_and_render() -> list[tuple[Document, str]]:
    """Nhu extract(), nhung tra ve noi dung file .md day du (front matter + than)."""
    return [(doc, render_markdown_file(doc, body_md)) for doc, body_md in extract()]
