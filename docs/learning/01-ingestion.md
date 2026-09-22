# Bước 1: Data ingestion (Collect/Crawl → Markdown)

Corpus: chính sách GSM (Green SM) cho khách hàng đi xe. Nguồn chính là greensm.com; thêm thông tin crawl từ internet (có nhãn tin cậy); tài liệu nội bộ bổ sung sau.

## Kết quả kiểm kê greensm.com (2026-09-21, sửa lớn 2026-09-22)

Đọc HTML thật bằng HTTP, không qua công cụ tóm tắt. `robots.txt` cho phép `/vn-vi` (chỉ chặn các vùng ID, NL, US). Sitemap `vn-vi` có 3.821 URL, trong đó 3.774 là bài tin tức.

**Sửa 2026-09-22 — hầu hết nội dung nằm trong `__NEXT_DATA__` (JSON), không phải DOM.** Bắt tay viết extractor mới phát hiện: bản kiểm kê 2026-09-21 kết luận "trang chính sách không có toàn văn trong JSON, văn bản nằm trong DOM" cho Quy định chung và Privacy — **sai**. Fetch lại và duyệt hết `props.pageProps` (không chỉ tìm một cụm từ rồi kết luận) cho kết quả khác hẳn:

| Trang | URL đúng | Dạng | Số ký tự | Ghi chú |
|---|---|---|---|---|
| Quy định chung | `/vn-vi/terms-policies/general` | JSON: `pageProps.generalTerms.generalItems[]`, mỗi phần tử có `title` + `description` sạch | ~226.000 (không phải ~11,6k **từ** như trước) | **16 văn bản**, không phải 1: `[0]` "Điều khoản sử dụng" (văn bản chính, 51.201 ký tự) + `[1..15]` 15 Phụ lục — tất cả đều ghi rõ áp dụng cho **Khách Hàng**, kể cả các phụ lục nghe như dành cho vận hành (xem bảng "Phạm vi đã chọn"). Đánh số `1.`/`1.1.`/`1.1.1.` nằm trong `description`, ngăn dòng bằng `\r\n`; hiệu lực 07/08/2026 nằm ngay trong `description[0]`, không phải regex chân trang |
| Chính sách bảo vệ dữ liệu cá nhân | `/vn-vi/terms-policies/privacy-notice` | JSON: `pageProps.privacyNotice.privacyItems[]` | ~55.000 | **14 mục đã đánh số + đặt tên sẵn** ("1. GIẢI THÍCH TỪ NGỮ" … "14. HIỆU LỰC") — không cần tự dựng heading cấp 1, JSON đã làm sẵn; hiệu lực từ 31/07/2026 |
| Hợp đồng dịch vụ | `/vn-vi/terms-policies/service-agreement` | JSON: `pageProps.serviceData.serviceItems[]`, cùng khuôn dạng | Chưa đo | Mở đầu (`serviceExcerpt`) ghi rõ áp dụng cho "Người Dùng ... và Đơn Vị Kinh Doanh Vận Tải" — vẫn có vẻ là hợp đồng vận hành giữa hai bên, không phải điều khoản một chiều cho khách; giữ nguyên kết luận "ngoài phạm vi", chỉ sửa URL |
| Quy chế hoạt động | `/vn-vi/terms-policies/regulations` | **56 ảnh JPG** (`quychehoatdong-1…56`) | — | Kiểm lại `pageProps`: chỉ có `_nextI18Next`, không có text. Kết luận OCR không đổi, chỉ sửa URL |
| Bảo hiểm khách hàng | `/vn-vi/bao-hiem-khach-hang` | JSON: `pageProps.insuranceData.{columns, rows}` | ~1,1k | Đúng như bản trước — bảng sạch trong JSON |
| Điều khoản ví E-Green | *(chưa tìm lại được)* | — | — | URL `/e-green-wallet-payment-terms` không còn trong sitemap; tìm cả 16 `generalItems` không thấy nhắc "E-Green" hay "Ví". Có thể đã gộp/đổi tên/gỡ bài — **chưa loại khỏi phạm vi, cần xác nhận lại trước khi ingest** |
| FAQ | `/vn-vi/helps` | JSON: `contentFaq.setUpFaq` | ~2,5k (DOM) | Kiểm lại, số liệu không đổi: 4 nhóm, 136 Q&A; "Dành cho người dùng" 49 câu/6 danh mục |
| Tin tức | `/vn-vi/news/*` | Text, có ngày | 3.774 bài | Không đổi |

FAQ "Dành cho người dùng" có 6 danh mục: An toàn (7), Di chuyển và dịch vụ khác (20), Cước phí và thanh toán (9), Khuyến mãi (5), Tài khoản và bảo mật dữ liệu (4), Ứng dụng (4).

**Trùng nội dung cần xử lý:** `generalItems[12]` ("CHÍNH SÁCH BẢO VỆ DỮ LIỆU CÁ NHÂN", 46.843 ký tự, một khối chưa tách mục) là bản sao gần như nguyên văn của trang `privacy-notice` riêng (đã tách sẵn 14 mục có tiêu đề). Dùng trang `privacy-notice` làm nguồn chính, **bỏ qua** `generalItems[12]` khi ingest — tránh index trùng 2 lần cùng một nội dung dưới 2 `chunk_id` khác nhau.

**Đính chính so với bản trước** (công cụ tóm tắt sai hoặc không có bằng chứng):
- Không có "Điều 1–18": văn bản đánh số thập phân, không có chữ "Điều".
- Không thấy trang quy định riêng từng dịch vụ (Car, Bike, Express…) trong sitemap. Số trang cần OCR là 56, không phải "vượt xa 50".
- Đồ thất lạc có trong FAQ 2.13, không phải chưa thấy.
- FAQ: câu trả lời **không** nằm sẵn trong DOM (chỉ mục đầu mỗi danh mục), tôi đã kết luận sai vì chỉ thử mục 1.1. Đầy đủ nằm trong `__NEXT_DATA__`. Các "tab" Doanh nghiệp, Đối tác tài xế, Bảo hiểm tôi nêu trước là mục điều hướng của site, không phải tab FAQ; FAQ có 4 nhóm đối tượng: người dùng, tài xế Taxi, tài xế Bike, Nhà hàng.
- **(2026-09-22)** "Trang chính sách không có toàn văn trong JSON" — sai. Quy định chung, Privacy, Bảo hiểm, Hợp đồng dịch vụ đều có toàn văn sạch trong `__NEXT_DATA__`. Chỉ Quy chế hoạt động (ảnh) thực sự không có JSON. Word count "~11,6k" của Quy định chung cũng sai — đó là kích thước một khối DOM (chỉ tab mặc định "Điều khoản sử dụng"), không phải toàn bộ 16 văn bản.

**Nhiễu mỗi trang (chỉ còn áp dụng cho DOM/OCR, không áp dụng cho các trang đọc JSON ở trên):** thanh điều hướng đầu trang, chân trang (giấy phép, © 2026 GSM). `description`/`title` trong JSON không lẫn nav/footer vì đó là nội dung Next.js hydrate riêng, không phải toàn bộ DOM đã render — chỉ còn phải loại nav/footer khi OCR Quy chế hoạt động hoặc khi rơi vào trang thật sự cần cạo DOM. Regex ngày từng lấy nhầm ngày giấy phép (01/03/2023, 23/09/2025, 13/12/2023) khi thử trên DOM — không còn là vấn đề khi đọc thẳng `description`.

**Cấu trúc chuỗi trong JSON:** mỗi `description` là một chuỗi dài (lớn nhất 51.201 ký tự) ngăn đoạn bằng `\r\n\r\n`. Số thứ tự (`1.`, `1.1.`) chỉ thấy sau khi tách theo `\r\n`, giống nguyên tắc "tách theo dòng" đã đặt ra trước đó — chỉ khác nguồn tách là chuỗi JSON, không phải text từ DOM.

## Độ phủ chủ đề

| Chủ đề bạn liệt kê | Công khai? | Nơi có |
|---|---|---|
| Đặt xe | Có | FAQ 2.1–2.7 |
| Thay đổi chuyến, hủy chuyến | Có | FAQ 2.8–2.10, 3.2; tin "tính năng hủy chuyến hợp lệ" (13/05/2025) |
| Giá và thanh toán | Có | FAQ nhóm 3; Quy định chung mục 3; ví E-Green **chưa xác nhận còn tồn tại** (xem bảng kiểm kê) |
| Hoàn tiền | Một phần, **cần đọc lại** | FAQ 3.6–3.9 (tình huống cụ thể); Phụ lục 7/8/9 (thuê xe, vận tải trả trước/trả sau) chưa đọc toàn văn, có thể có điều khoản hoàn tiền — thêm vào việc cần làm |
| Khiếu nại và CSKH | **Có** (sửa 2026-09-22, trước ghi "Một phần") | FAQ 6.4, hotline 1555, email hỗ trợ; **Phụ lục 15 "QUY TRÌNH GIẢI QUYẾT TRANH CHẤP, KHIẾU NẠI"** — toàn văn công khai, không còn là "quy trình nội bộ không công khai" như đã đoán trước đó |
| Đồ thất lạc | Một phần | FAQ 2.13 |
| Privacy | Có | Chính sách bảo vệ dữ liệu cá nhân (14 mục); FAQ 5.4 |
| Security (an toàn thông tin), SLA, RBAC | Không | Chờ tài liệu nội bộ. Nhóm "An toàn" của FAQ là an toàn chuyến đi |

Câu hỏi thuộc các chủ đề "Không" phải rơi vào nhánh "không biết" và có mặt trong bộ eval.

## Phạm vi đã chọn (khách hàng đi xe)

Sửa 2026-09-22: "Quy định chung" không còn là 1 dòng — tách thành 16 tài liệu độc lập theo `generalItems[]`, mỗi cái một `doc_id` riêng (xem "Đặt doc_id" bên dưới).

| Tài liệu | Vào index | Cách lấy |
|---|---|---|
| Điều khoản sử dụng (`generalItems[0]`) | Có | Đọc JSON, tách theo `\r\n`, dựng heading từ số thứ tự |
| 15 Phụ lục của Điều khoản sử dụng (`generalItems[1..15]`) | Có — mở đầu mỗi phụ lục đều ghi rõ áp dụng cho Khách Hàng | Đọc JSON, mỗi phần tử một tài liệu |
| Chính sách bảo vệ dữ liệu cá nhân (14 mục, trang riêng) | Có | Đọc JSON `privacyItems[]`; **bỏ qua** bản sao ở `generalItems[12]` (trùng nội dung) |
| FAQ "Dành cho người dùng" (49 câu) | Có | Đọc JSON `contentFaq.setUpFaq` |
| Bảo hiểm khách hàng (Green SM Care) | Có | Đọc JSON `insuranceData.{columns, rows}` |
| Quy chế hoạt động (56 ảnh) | Có | Tải ảnh → Docling + OCR local |
| Điều khoản ví E-Green | Tạm hoãn | URL cũ không còn; chưa tìm thấy vị trí mới — xác nhận trước khi ingest, không tự ý bỏ khỏi phạm vi |
| Hợp đồng dịch vụ | Không | Mở đầu ghi rõ áp dụng cho "Đơn Vị Kinh Doanh Vận Tải"; thêm lại nếu bạn muốn |
| FAQ tài xế Taxi (15), tài xế Bike (26), Nhà hàng (46) | Không | Ngoài phạm vi khách hàng; có sẵn trong cùng JSON nếu cần |
| Tin tức (3.774 bài) | Chưa quyết | Bạn chọn "tính sau" |

## Đặt `doc_id` cho các tài liệu tách từ `generalItems`

Slug theo tiêu đề, đánh số phụ lục theo đúng số trong `title` gốc để không lệch với chính văn bản (văn bản tự ghi "PHỤ LỤC N"):

```
dieu-khoan-su-dung                    generalItems[0]
phu-luc-01-quy-trinh-nguoi-dung        generalItems[1]
phu-luc-02-quy-che-car                generalItems[2]
phu-luc-03-quy-che-bike                generalItems[3]
...                                     (tiếp tục theo cùng khuôn tới phụ lục 15)
phu-luc-15-giai-quyet-khieu-nai        generalItems[15]
chinh-sach-du-lieu-ca-nhan             privacyNotice (trang riêng)
bao-hiem-khach-hang                    insuranceData
faq                                     contentFaq (giữ tên như Bước 2 đã dùng: faq#3.6)
quy-che-hoat-dong                       56 ảnh OCR
```

`doc_type` cho toàn bộ nhóm `generalItems`: `dieu_khoan` (khớp Bước 2). Mọi phụ lục vẫn cần gắn `doi_tuong` theo khoản như đã quyết ở Bước 2 — phụ lục 15 tự nhắc tới "Tài Xế, Đối Tác, Thương Nhân" nên chắc chắn có khoản không phải `nguoi_dung`.

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Web (greensm.com) | **`httpx` + đọc `__NEXT_DATA__`** (sửa 2026-09-22: không phải "bộ trích DOM", vì hầu hết trang đều có JSON sạch) | Toàn bộ Quy định chung, Privacy, Bảo hiểm, Hợp đồng dịch vụ, FAQ đều có `title`/`description` sẵn trong `pageProps`; chỉ cần `json.loads` + tách theo `\r\n`, không cần bộ trích DOM/regex nav-footer. Bộ trích DOM tự viết chỉ còn dự phòng cho trang thật sự không có JSON |
| Web cần JS (tab FAQ, site ngoài) | Crawl4AI, dự phòng | Chỉ dùng khi thật sự cần |
| Quy chế hoạt động | Tải 56 ảnh theo thứ tự → **Docling + OCR local** → Markdown có dấu ngắt trang | Một tài liệu, 56 trang, đủ nhỏ để chạy local |
| File nội bộ (sau) | Docling (PDF, DOCX, XLSX…) | Cùng đường với ảnh/PDF |
| Lưu trữ | File gốc trước, Markdown là bản dẫn xuất | Đổi converter không phải crawl hay OCR lại |
| Citation | Nguồn (URL) + đường dẫn heading; ảnh/PDF thêm số trang | Mỗi ảnh là một trang nên số trang gần như miễn phí |
| Độ tin cậy nguồn | Nhãn `nguon_tin_cay`; mặc định chỉ index nguồn chính thức | Tránh trả lời chính sách theo tin đồn hoặc bài cũ |
| Tài liệu nội bộ | Nhãn `audience`, index tách riêng | Khách không bao giờ thấy tài liệu nội bộ |
| Phiên bản | Chỉ bản hiện hành; `ngay_hieu_luc` trích bằng regex từ phần thân, sau khi loại chân trang | Trang chỉ công bố bản hiện hành |
| Tiếng Việt | Chuẩn hóa **NFC** sau convert | Chữ như "ệ" có hai dạng Unicode; không chuẩn hóa thì BM25 và so khớp chuỗi trượt nhau |

## Nguồn và độ tin cậy

| Nhóm | Ví dụ | `nguon_tin_cay` | Index mặc định |
|---|---|---|---|
| Chính thức | greensm.com: điều khoản, chính sách, FAQ, Quy chế (ảnh) | `chinh_thuc` | Có |
| Chính thức, có ngày | Tin tức trên greensm.com (bài thông báo tính năng, chính sách) | `chinh_thuc` | Không mặc định; chọn tay vài bài |
| Báo chí | Bài về chính sách hủy chuyến, đồ thất lạc | `bao_chi` | Không; nếu dùng thì gắn nhãn "tham khảo" |
| Cộng đồng, đại lý | Diễn đàn, site đại lý (đã gặp trong kết quả tìm kiếm) | `cong_dong` | Không: có thể sai hoặc lỗi thời |
| Nội bộ (bổ sung sau) | SLA, RBAC, quy trình CSKH, security | `noi_bo` | Không cho khách: index tách riêng |

## Web: phương án

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| `httpx` + đọc `__NEXT_DATA__`, chỉ dựng bộ trích DOM khi trang thật sự không có JSON | Nhẹ; JSON đã tách sẵn theo tài liệu/mục, không cần đoán ranh giới từ text phẳng | Cấu trúc JSON không đồng nhất 100% giữa các trang (mỗi trang một tên key: `generalTerms`, `privacyNotice`, `insuranceData`...), phải xem từng trang | **Chọn** cho greensm.com |
| Crawl4AI 0.9 (Apache-2.0) | Chạy JS (Playwright), crawl BFS, `fit_markdown` lọc nhiễu | Phải cài Chromium, nhiều thứ ẩn bên trong | Dự phòng cho trang cần JS |
| trafilatura 2.2 | Tách nội dung chính tốt | Chưa thử trên các trang này; có nguy cơ gộp các dòng đánh số | Thử để so, chưa chọn |
| Firecrawl, Jina Reader | Ít công nhất | Dịch vụ ngoài, tốn phí/key | Không chọn |
| Scrapy, Playwright + BeautifulSoup tự viết | Kiểm soát tối đa | Tốn công ở phần không thuộc RAG | Không chọn |

## Convert / OCR: phương án

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| Docling 2.129 (MIT) | Layout, bảng, nhận ảnh PNG/JPEG/TIFF, nhiều engine OCR, chạy arm64 | Nặng, tải model lần đầu | **Chọn** |
| MarkItDown 0.1.7 | Rất nhẹ | PDF chủ yếu trích text, không hợp tài liệu ảnh | Không chọn |
| pymupdf4llm | Rất nhanh | AGPL (dual-license) | Không chọn |
| Marker 2.0 | Chất lượng cao | Trọng số model giới hạn thương mại; Apple Silicon cần thêm `llama-server` | Không chọn |
| unstructured 0.27 | Nhiều loại tài liệu | Không hỗ trợ Python 3.14, nhiều dependency | Không chọn |
| LlamaParse, Mistral OCR, Gemini vision | Mạnh với ảnh quét, chuẩn dấu | Tốn phí; bạn đã chọn chỉ local | Không chọn lúc này; có thể xét lại vì dữ liệu GSM công khai |

**Engine OCR (ứng viên, đo ở bake-off):** EasyOCR (`vi`), OcrMac (Apple Vision, cần kiểm tra có hỗ trợ tiếng Việt), Tesseract (`vie`, phải `brew install`), RapidOCR. Dự đoán từ tài liệu ngoài: Tesseract hay sai dấu hơn EasyOCR. Chưa đo.

## Layout dữ liệu

```
data/raw/
  web/        HTML gốc
  images/     ảnh trang tài liệu, đặt tên theo thứ tự
  internal/   file nội bộ (bổ sung sau)
data/markdown/   <doc_id>.md
```

Front matter mỗi file Markdown: `source`, `title`, `doc_type`, `audience`, `nguon_tin_cay`, `fetched_at`, `content_hash`, `ngay_hieu_luc` nếu có. `content_hash` để bỏ qua tài liệu không đổi.

## Dựng heading

Không tin heading do converter suy ra; dựng từ khung của chính tài liệu, tách theo dòng:
- Điều khoản: `1.` + tiêu đề in hoa → `#`; `1.1.` → `##`; `1.1.1.` → `###`. Mức `1.1.` thường là cả một điều khoản chứ không phải tiêu đề: Bước 2 quyết định coi nó là đơn vị chunk.
- FAQ: nhóm (1–6) → `#`; câu hỏi (1.1…) → `##`.
- Quy chế (ảnh): chạy cùng regex sau OCR, kiểm tra tay vì OCR có thể sai số.

Cây PageIndex khi đó chính là khung của tài liệu.

## Cần kiểm chứng khi làm

- Bake-off OCR trên 3–5 ảnh trong 56 ảnh của Quy chế: đo tỉ lệ ký tự sai, soi dấu tiếng Việt.
- Tìm lại Điều khoản ví E-Green: thử sitemap các locale khác, thử tìm trong nav/footer của trang chủ, hoặc hỏi trực tiếp — đừng đoán nó đã bị gộp vào phụ lục nào mà không có bằng chứng.
- Đọc toàn văn Phụ lục 7/8/9 (thuê xe, vận tải trả sau/trả trước) để xác nhận có điều khoản hoàn tiền hay không — mới đọc ~280 ký tự đầu mỗi phụ lục, chưa đủ để kết luận.
- Xác nhận `generalItems[12]` và `privacyItems[]` giống nhau đến mức nào (đã thấy đoạn mở đầu giống hệt, chưa so toàn văn) trước khi quyết định bỏ hẳn `generalItems[12]`.
- Trafilatura/`fit_markdown` không còn cần thiết cho các trang đã xác nhận có JSON; chỉ còn đáng thử nếu sau này gặp trang thật sự phải cạo DOM.

## Khi nào đổi

- Trang cần JS xuất hiện nhiều → đường chính chuyển sang Crawl4AI.
- OCR local sai dấu nhiều → hỏi bạn về API vision OCR (dữ liệu công khai nên không còn rào cản bảo mật, chỉ còn chi phí).
- Thêm nguồn ngoài → gắn nhãn tin cậy, không index mặc định.

## Bài học

- Một mẫu đúng chưa đủ để kết luận: tôi báo "câu trả lời FAQ có sẵn trong HTML" chỉ vì mục 1.1 có, thực tế mỗi danh mục chỉ mở sẵn một mục. Kiểm tra mọi phần tử, không kiểm một mẫu.
- Trang Next.js thường nhúng dữ liệu có cấu trúc trong `__NEXT_DATA__`: nguồn sạch và đầy đủ hơn cạo HTML.
- Kiểm kê bằng HTML thật trước khi thiết kế: công cụ tóm tắt đã bịa "Điều 1–18" và các trang quy định riêng từng dịch vụ.
- Bộ trích tổng quát (trafilatura, `fit_markdown`) có thể phá cấu trúc dòng; văn bản đánh số cần bộ trích tôn trọng dòng.
- Loại thanh điều hướng và chân trang trước khi index và trước khi regex ngày.
- Chọn công cụ theo **loại nguồn**, không theo độ nổi tiếng.
- **Heading là hợp đồng** giữa ingest, PageIndex và citation.
- Crawl rộng thì nguồn có thứ hạng tin cậy: nội dung sai lệch về chính sách còn tệ hơn không có nội dung.
- Tiếng Việt có hai bẫy ngay từ đầu: Unicode NFC và dấu khi OCR.
- Giữ file gốc, vì OCR là bước tốn thời gian nhất và không nên chạy lại.
- **(2026-09-22)** Kết luận "không có" khó hơn kết luận "có": tìm một cụm từ, không thấy, rồi kết luận "trang này không có toàn văn trong JSON" là kiểu suy luận từ một mẫu âm tính — cùng lỗi với bài học FAQ ở trên nhưng ngược chiều. Phải duyệt hết cấu trúc (`json.dumps` rồi tìm key, hoặc đệ quy qua toàn bộ `dict`/`list`) trước khi kết luận một nguồn "không tồn tại".
- Một URL trong tài liệu cũ có thể đã lệch khỏi thực tế (ví dụ `/privacy-notice` → `/terms-policies/privacy-notice`) dù nội dung nó mô tả vẫn đúng hướng — luôn tự tay xác nhận URL bằng sitemap thật ngay trước khi viết code gọi vào nó, không tin URL đã ghi trong tài liệu brainstorm.
