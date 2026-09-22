"""Extractor cho '/vn-vi/terms-policies/privacy-notice' (Chinh sach bao ve
du lieu ca nhan, 14 muc).

Nguon: pageProps.privacyNotice.privacyItems[] - moi phan tu da co san
title dang "N. TIEU DE" (khong can heading.classify_line doan lai, chi
can dinh dang thanh H1), va description la than muc do (co the con
danh so con ben trong, van chay qua heading.to_markdown de bat).
"""

from __future__ import annotations

import datetime as _dt

from rag_gsm.ingest import heading
from rag_gsm.ingest.normalize import make_document, render_markdown_file
from rag_gsm.ingest.web import fetch_next_data
from rag_gsm.schemas import Document

PATH = "/vn-vi/terms-policies/privacy-notice"
SOURCE_URL = f"https://www.greensm.com{PATH}"
DOC_ID = "chinh-sach-du-lieu-ca-nhan"


def extract() -> tuple[Document, str]:
    data = fetch_next_data(PATH)
    pn = data["props"]["pageProps"]["privacyNotice"]
    items = pn["privacyItems"]
    fetched_at = _dt.date.today().isoformat()

    sections: list[str] = []
    full_text_for_hash: list[str] = []
    for item in items:
        title_line = heading.classify_line(item["title"].strip())
        if title_line.level == 0:
            # Phong khi mot muc khong theo dung khuon "N. TIEU DE" - van
            # giu lam H1 de khong mat noi dung, nhung dang la dau hieu can xem lai.
            heading_md = f"# {item['title'].strip()}"
        else:
            heading_md = f"# {title_line.so_muc}. {title_line.text}"
        body_md = heading.to_markdown(item["description"])
        sections.append(f"{heading_md}\n\n{body_md}")
        full_text_for_hash.append(item["title"])
        full_text_for_hash.append(item["description"])

    body_markdown = "\n\n".join(sections)
    doc = make_document(
        doc_id=DOC_ID,
        source=SOURCE_URL,
        title=pn.get("privacyTitle", "Chính sách bảo vệ dữ liệu cá nhân"),
        doc_type="chinh_sach",
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at=fetched_at,
        body_text="\n".join(full_text_for_hash),
        markdown_path=f"data/markdown/{DOC_ID}.md",
    )
    return doc, body_markdown


def extract_and_render() -> tuple[Document, str]:
    doc, body_md = extract()
    return doc, render_markdown_file(doc, body_md)
