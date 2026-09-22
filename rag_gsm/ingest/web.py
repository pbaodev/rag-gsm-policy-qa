"""Fetch trang greensm.com va lay JSON __NEXT_DATA__.

Phat hien 2026-09-22: hau het trang can (Quy dinh chung, Privacy, Bao
hiem, Hop dong dich vu, FAQ) deu co toan van sach trong __NEXT_DATA__,
khong can bo trich DOM. Xem docs/learning/01-ingestion.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

BASE_URL = "https://www.greensm.com"
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)

# Buoc 1 da chot "File goc truoc, Markdown la ban dan xuat" - luu HTML tho
# truoc khi parse, de doi cach trich khong phai fetch lai (phat hien
# 2026-09-22: ban dau fetch_html chi tra ve text trong bo nho, khong luu).
RAW_WEB_DIR = Path("data/raw/web")

_client: httpx.Client | None = None


def _slug_for_path(path: str) -> str:
    return path.strip("/").replace("/", "_") + ".html"


def _save_raw_html(path: str, html: str) -> None:
    RAW_WEB_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_WEB_DIR / _slug_for_path(path)).write_text(html, encoding="utf-8")


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0 (rag-gsm ingest; hoc tap ca nhan)"},
        )
    return _client


def fetch_html(path: str, *, save_raw: bool = True) -> str:
    """Fetch mot duong dan tuong doi (vd '/vn-vi/terms-policies/general').

    Mac dinh luu HTML tho vao data/raw/web/ truoc khi tra ve - dung
    save_raw=False cho cac lan fetch phu (vd kiem tra nhanh) khong can luu.
    """
    url = f"{BASE_URL}{path}"
    resp = _get_client().get(url)
    resp.raise_for_status()
    if save_raw:
        _save_raw_html(path, resp.text)
    return resp.text


def fetch_next_data(path: str) -> dict:
    """Fetch trang va tra ve du lieu __NEXT_DATA__ da parse."""
    html = fetch_html(path)
    m = _NEXT_DATA_RE.search(html)
    if not m:
        raise ValueError(f"Khong tim thay __NEXT_DATA__ trong {path}")
    return json.loads(m.group(1))
