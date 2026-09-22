"""Extractor cho '/vn-vi/helps' (FAQ), chi lay nhom "Danh cho nguoi dung".

Nguon: pageProps.contentFaq.setUpFaq - 4 nhom doi tuong (nguoi dung, tai
xe Taxi, tai xe Bike, Nha hang), moi nhom co setUpQuestion (danh muc),
moi danh muc co setUpTitle (cau hoi: {label, value}). Doc JSON, khong cao
DOM (DOM chi mo san 1 cau tra loi moi danh muc - bai hoc Buoc 1).

Danh so: danh muc (1-6) -> H1, cau hoi (vd 1.1) -> H2 (Buoc 1 "Dung
heading"). Cac buoc "1/ 2/ ..." trong cau tra loi giu nguyen lam than
van ban, khong chay qua heading.to_markdown (khac khuon "N." nen khong
bi nham thanh tieu de).
"""

from __future__ import annotations

import datetime as _dt

from rag_gsm.ingest import heading
from rag_gsm.ingest.normalize import make_document, render_markdown_file
from rag_gsm.ingest.web import fetch_next_data
from rag_gsm.schemas import Document

PATH = "/vn-vi/helps"
SOURCE_URL = f"https://www.greensm.com{PATH}"
DOC_ID = "faq"
TARGET_GROUP = "Dành cho người dùng"


def _clean_answer(value: str) -> str:
    # Vai cau tra loi co the <a href="...">lien ket</a> (vd toi trang Bao
    # hiem khach hang) - strip_inline_html doi thanh Markdown [text](URL)
    # roi lot cac the con lai (phat hien 2026-09-22).
    text = heading.strip_inline_html(value)
    return text.replace("\r\n", "\n").strip()


def extract() -> tuple[Document, str]:
    data = fetch_next_data(PATH)
    setup_faq = data["props"]["pageProps"]["contentFaq"]["setUpFaq"]

    group = next((g for g in setup_faq if g["question"] == TARGET_GROUP), None)
    if group is None:
        available = [g["question"] for g in setup_faq]
        raise ValueError(
            f"Khong tim thay nhom '{TARGET_GROUP}' - nhom co san: {available}. "
            "Site co the da doi ten nhom, xem lai truoc khi ingest tiep."
        )

    fetched_at = _dt.date.today().isoformat()
    sections: list[str] = []
    full_text_for_hash: list[str] = []
    total_questions = 0

    for cat_idx, category in enumerate(group["setUpQuestion"], start=1):
        cat_title = heading.strip_inline_html(category["title"]).strip()
        sections.append(f"# {cat_idx}. {cat_title}")
        full_text_for_hash.append(cat_title)
        for q_idx, qa in enumerate(category["setUpTitle"], start=1):
            question = heading.strip_inline_html(qa["label"]).strip()
            answer = _clean_answer(qa["value"])
            sections.append(f"## {cat_idx}.{q_idx}. {question}\n\n{answer}")
            full_text_for_hash.append(question)
            full_text_for_hash.append(answer)
            total_questions += 1

    body_markdown = "\n\n".join(sections)
    doc = make_document(
        doc_id=DOC_ID,
        source=SOURCE_URL,
        title="Trung tâm giải đáp - Dành cho người dùng",
        doc_type="faq",
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
