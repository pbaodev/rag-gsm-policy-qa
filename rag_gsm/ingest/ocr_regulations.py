"""Buoc 1 (OCR): 'Quy che hoat dong' (56 anh JPG tai
/vn-vi/terms-policies/regulations, xem docs/learning/01-ingestion.md).

Day la script THU CONG, khac voi cac extractor JSON trong extractors/ -
khong nam trong `ingest.run` (khong "an toan chay lai bat ky luc nao" nhu
cac trang JSON, vi can nguoi kiem tra chat luong OCR truoc khi dung).

Bake-off OCR that (2026-09-23) tren 3 anh mau (trang 1, 30, 56), so
EasyOcrOptions / OcrMacOptions / RapidOcrOptions cua Docling:
- OcrMac (Apple Vision, co san tren macOS, khong can tai gi them) THANG
  ro: ~4-5s/trang, dau tieng Viet gan hoan hao, dung thu tu doc.
- EasyOCR: cham (44s/trang) VA lon thu tu doc o tieu de 2 cot (doan van
  bi xao tron tu, mat chu).
- RapidOCR (mac dinh): nhanh nhung model mac dinh la tieng Trung - gan
  nhu MAT HET dau tieng Viet ("CÔNG TY C PHÀN" thay vi "CÔNG TY CỔ PHẦN").
Ket luan: dung OcrMacOptions(lang=["vi-VT"]) - macOS Vision bao cao ma
ngon ngu Tieng Viet la "vi-VT" (khong phai "vi"/"vi-VN" chuan BCP-47),
day la quirk that cua framework, khong phai loi cau hinh.

Phat hien lon hon khi chay OCR full-page tren CA 56 trang: day KHONG
phai mot van ban "quy che" dong nhat.
- Trang 1-2: tieu de + "A. Nguyen tac va quy dinh chung".
- Trang ~2-42: "B.1 Quy trinh danh cho Khach Hang" (huong dan tung buoc
  kem anh chup man hinh) roi "Quy trinh danh cho Tai Xe" (ngoai pham vi
  khach hang). Tren cac trang dang BANG 2 cot (chu + anh chup man hinh),
  pipeline OCR theo trang cua Docling nhieu luc MAT TRANG chu that (17/56
  trang, ~30%, chi ra placeholder "<!-- image -->") du chu de dam ("Buoc
  2: Tao tai khoan...") ro rang trong anh goc - loi phan loai layout
  (ca trang bi coi la 1 anh), khong phai loi dau tieng Viet. Phan lon
  noi dung "cach dat xe/tao tai khoan" o day cung da co san sach hon
  trong FAQ (JSON that, xem extractors/faq.py).
- Trang 43-46: quay lai van ban phap ly that (quy trinh doi tra/hoan
  tien, giai quyet tranh chap khieu nai, cac phuong thuc thanh toan) -
  co gia tri that cho khach hang, OCR dang tin cay (khong phai dang bang
  anh chup).
- Trang 47-51: "C. Hoat dong dich vu khuyen mai truc tuyen" - lai la
  bang cau truc/man hinh minh hoa, cung van de OCR nhu tren - BO QUA.
- Trang 52-56: van ban phap ly (quyen/trach nhiem BQL san, dieu kien tro
  thanh Doi Tac/Thuong Nhan, dieu khoan cam ket, ky ten). Trang 53-55 co
  danh so bi OCR doc SAI - lap lai "1.1.1." cho nhieu muc khac nhau
  khong lien quan (kiem tra tay bang anh goc: day la loi doc nham cua
  OCR/dinh dang danh sach goc, khong phai that). KHONG dung nhung so do
  lam `so_muc` (se dam chunk_id) - dua vao co che "gom theo kich thuoc"
  da co san cho van ban khong danh so dang tin cay (giong phu-luc-01/13/15,
  xem rules.py).

Quyet dinh pham vi (nguoi dung chon, khong tu y): CHI OCR/index trang
1-2 va 43-56 (van ban phap ly that) - BO QUA toan bo phan huong dan tung
buoc dang bang/anh chup (trang 3-42, 47-51) vi (a) OCR khong dang tin
cay tren dang bang 2 cot, (b) phan lon noi dung da trung FAQ.

Phat hien phu: tim thay 4 thong tin lien he KHAC NHAU rai rac trong
chinh corpus - hotline "1555" (FAQ), "1900 2097"/"19002097" (trang 43/45
cua chinh Quy che nay, "To chuc xa hoi" khieu nai), "1800 1066" (trang
56, chan trang Quy che), email "support.vn@greensm.com" (FAQ + trang 56)
vs "cskh@xanhsm.com" (trang 45, domain KHAC "xanhsm.com" thay vi
"greensm.com"). Ghi lai trung thuc ca 2 so o day, KHONG tu chon 1 so
"dung nhat" - can nguoi that xac nhan so nao con hieu luc.

Van ban than sau day la ban da CON NGUOI/AI doc lai va sua loi OCR ro
rang (dau bi mat, chu bi lap/thieu) tu output OCR that (script
`ocr_page()` ben duoi) - khong phai sinh may moc hoan toan. Neu OCR lai
(vd dung engine tot hon sau nay) thi phai doc lai va sua tay lan nua,
khong the tu dong ghi de ban da sua.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import httpx

from rag_gsm.ingest.normalize import make_document
from rag_gsm.schemas import Document

REGULATIONS_PAGE_URL = "https://www.greensm.com/vn-vi/terms-policies/regulations"
IMAGE_URL_TEMPLATE = "https://www.greensm.com/images/regulations/quychehoatdong-{n}.jpg"
RAW_IMAGES_DIR = Path("data/raw/images")
TOTAL_PAGES = 56

# Trang van ban phap ly dang tin cay (xem docstring o tren cho ly do chon/bo).
SELECTED_PAGES = [1, 2, 43, 44, 45, 46, 52, 53, 54, 55, 56]

DOC_ID = "quy-che-hoat-dong"
_BODY_PATH = Path(__file__).parent / "quy_che_hoat_dong_body.md"


def download_images() -> None:
    """Tai ca 56 anh trang ve data/raw/images/ (idempotent, an toan chay
    lai). Dung URL static truc tiep, KHONG qua proxy /_next/image cua
    Next.js - proxy tra anh da nen/giam kich thuoc, anh static giu dung
    do phan giai goc (quan trong cho OCR)."""
    RAW_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers={"User-Agent": "Mozilla/5.0 (rag-gsm ingest; hoc tap ca nhan)"}, timeout=20)
    for n in range(1, TOTAL_PAGES + 1):
        path = RAW_IMAGES_DIR / f"quychehoatdong-{n}.jpg"
        if path.exists():
            continue
        resp = client.get(IMAGE_URL_TEMPLATE.format(n=n))
        resp.raise_for_status()
        path.write_bytes(resp.content)


def ocr_page(n: int) -> str:
    """OCR 1 trang bang Docling + OcrMac (macOS Vision) - xem docstring
    module cho ket qua bake-off. Chi chay duoc tren macOS. Dung de
    KIEM TRA/DOI CHIEU lai ban da sua tay o quy_che_hoat_dong_body.md,
    khong dung de tu dong ghi de no."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, ImageFormatOption

    img_path = RAW_IMAGES_DIR / f"quychehoatdong-{n}.jpg"
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        # macOS Vision bao cao Tieng Viet la "vi-VT" (khong phai "vi"/"vi-VN"
        # chuan BCP-47) - quirk that cua framework, xem docstring module.
        ocr_options=OcrMacOptions(lang=["vi-VT"]),
        force_full_page_ocr=True,
    )
    converter = DocumentConverter(format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)})
    result = converter.convert(str(img_path))
    return result.document.export_to_markdown()


def extract() -> tuple[Document, str]:
    """Tra ve (Document, than Markdown) tu ban da sua tay
    (quy_che_hoat_dong_body.md) - KHONG goi OCR that (xem docstring)."""
    body_text = _BODY_PATH.read_text(encoding="utf-8")
    doc = make_document(
        doc_id=DOC_ID,
        source=REGULATIONS_PAGE_URL,
        title="Quy chế hoạt động ứng dụng cung cấp dịch vụ Green SM",
        doc_type="dieu_khoan",  # schemas.py du kien "quy_che" nhung chunk_document() chua co
        # nhanh rieng cho no va noi dung o day (heading + van xuoi) khop
        # dung khuon dieu_khoan da co - khong them doc_type/nhanh moi
        # chi de dat dung ten, tranh code du thua (Buoc 0.3).
        audience="khach_hang",
        nguon_tin_cay="chinh_thuc",
        fetched_at=_dt.date.today().isoformat(),
        body_text=body_text,
        markdown_path=f"data/markdown/{DOC_ID}.md",
    )
    return doc, body_text


def main() -> None:
    print("Tai anh goc ve data/raw/images/ ...")
    download_images()
    print(f"Da co du {TOTAL_PAGES} anh. Ghi markdown tu ban da sua tay ...")
    from rag_gsm.ingest.normalize import render_markdown_file

    doc, body_md = extract()
    Path(doc.markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(doc.markdown_path).write_text(render_markdown_file(doc, body_md), encoding="utf-8")
    print(f"  {doc.doc_id:20s} {len(body_md):6d} ky tu (trang {SELECTED_PAGES})")


if __name__ == "__main__":
    main()
