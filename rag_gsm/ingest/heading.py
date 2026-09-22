"""Dung heading tu khung so thu tu cua chinh van ban (Buoc 1).

Khong tin heading do converter suy ra. Ap dung cho van ban dang
`1. TIEU DE HOA` / `1.1.` / `1.1.1.` (Dieu khoan su dung, cac Phu luc,
Chinh sach bao ve du lieu ca nhan). Nguon van ban la chuoi JSON
(`description`) ngan doan bang "\\r\\n", khong phai DOM.

Muc `1.1.` thuong la ca mot dieu khoan chu khong phai tieu de rieng
(Buoc 2 se quyet dinh coi no la don vi chunk) - heading.py chi dung
so thu tu de xac dinh RANH GIOI dong, khong ep no phai la mot dong
tieu de ngan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "1." roi mot khoang trang - "1.1. X" khong khop vi sau dau cham dau tien
# la chu so, khong phai khoang trang, nen khong can loai truong hop do rieng.
_LEVEL1 = re.compile(r"^(\d{1,2})\.\s+(.*)$")
_LEVEL2 = re.compile(r"^(\d{1,2}\.\d{1,2})\.\s+(.*)$")
_LEVEL3 = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\.\s+(.*)$")

# Phat hien 2026-09-22: mot so Phu lục (vd Phu luc 2 - Quy che Car) danh
# dau tieu de bang <strong>1. Ten muc</strong> thay vi dong so tran (khac
# voi "Dieu khoan su dung" dung dong so tran khong the). Phai lot the
# truoc khi tach dong, khong thi so thu tu nam sau "<strong>" se khong
# khop dau dong va bi coi la than van ban - mat het heading cua phu luc do.
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_ANCHOR_RE = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)


def strip_inline_html(text: str) -> str:
    """Doi <a href="URL">text</a> thanh Markdown [text](URL) (gap trong FAQ,
    vd link toi trang Bao hiem khach hang), roi lot moi the con lai
    (<strong>, <i>...) - phat hien 2026-09-22, xem docs/learning/01-ingestion.md."""
    text = _ANCHOR_RE.sub(r"[\2](\1)", text)
    return _HTML_TAG_RE.sub("", text)


@dataclass
class HeadingLine:
    level: int  # 1, 2, 3, hoac 0 (khong phai dong tieu de, la than van ban)
    so_muc: str | None  # "1", "1.1", "1.1.1"
    text: str  # noi dung dong (da bo phan so thu tu neu la dong tieu de)


def split_lines(raw_text: str) -> list[str]:
    """Lot the HTML inline, chuan hoa xuong dong ve \\n, bo dong rong thua."""
    text = strip_inline_html(raw_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    return [ln for ln in lines if ln]


def classify_line(line: str) -> HeadingLine:
    """Nhan dien mot dong la tieu de cap may, hay chi la than van ban.

    Tu lot the HTML inline truoc khi so khop, de goi truc tiep tren mot
    dong/title rieng le (vi du title cua privacyItems) van an toan ke ca
    khi chua qua split_lines()."""
    line = strip_inline_html(line).strip()
    m3 = _LEVEL3.match(line)
    if m3:
        return HeadingLine(level=3, so_muc=m3.group(1), text=m3.group(2).strip())
    m2 = _LEVEL2.match(line)
    if m2:
        return HeadingLine(level=2, so_muc=m2.group(1), text=m2.group(2).strip())
    m1 = _LEVEL1.match(line)
    if m1:
        return HeadingLine(level=1, so_muc=m1.group(1), text=m1.group(2).strip())
    return HeadingLine(level=0, so_muc=None, text=line)


def to_markdown(raw_text: str) -> str:
    """Chuyen chuoi description thanh Markdown co # / ## / ###.

    Dong khong phai tieu de duoc giu nguyen lam than van ban.
    """
    out: list[str] = []
    for line in split_lines(raw_text):
        hl = classify_line(line)
        if hl.level == 0:
            out.append(hl.text)
        else:
            out.append(f"{'#' * hl.level} {hl.so_muc}. {hl.text}".rstrip())
    return "\n\n".join(out)


def check_numbering_continuity(raw_text: str) -> list[str]:
    """Tra ve danh sach canh bao neu so thu tu cap 1 khong lien tuc 1..N.

    Dung lam test doi chieu (Buoc "Test can viet" trong kien-truc-code.md):
    bat loi nhay so, ke ca loi OCR sau nay.
    """
    warnings: list[str] = []
    seen_level1: list[int] = []
    for line in split_lines(raw_text):
        hl = classify_line(line)
        if hl.level == 1 and hl.so_muc is not None:
            seen_level1.append(int(hl.so_muc))
    expected = list(range(1, len(seen_level1) + 1))
    if seen_level1 != expected:
        warnings.append(
            f"So thu tu cap 1 khong lien tuc: thay {seen_level1}, ky vong {expected}"
        )
    return warnings
