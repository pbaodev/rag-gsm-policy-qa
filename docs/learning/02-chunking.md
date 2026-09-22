# Bước 2: Chunking

Corpus: chính sách GSM cho khách hàng đi xe (FAQ, điều khoản, chính sách dữ liệu, ví E-Green, bảo hiểm, Quy chế hoạt động dạng ảnh).

## Dữ liệu thật quyết định

| Nhóm | Đặc điểm (đã kiểm kê) | Hệ quả |
|---|---|---|
| FAQ | 49 câu, 6 danh mục. Đo bằng tokenizer XLM-R: trung vị 160 token/cặp, p90 415, max 557, chỉ 2/49 vượt 512; có chuỗi bước đánh số | Hầu hết giữ nguyên; 2 cặp dài tách theo bước |
| Quy định chung, Chính sách dữ liệu cá nhân | 10–11k từ mỗi trang; đánh số `1.` / `1.1.` / `1.1.1.`. Đo trên Quy định chung: mục cấp 1 trung vị 418 token nhưng p90 3,3k (8/19 vượt 512); khối cấp 2 trung vị 66, p90 454, max 1.182 (7/87 vượt 512). **Sửa 2026-09-22: số đo này chỉ tính trên `generalItems[0]` ("Điều khoản sử dụng"), lúc đó tưởng là toàn bộ "Quy định chung" — thực ra còn 15 Phụ lục khác chưa đo (xem `01-ingestion.md`). Coi các con số median/p90 ở đây là tạm thời, đo lại khi code chunk thật, không dùng để chốt ngân sách token cuối cùng.** | Mục cấp 1 lớn và không đều, khối cấp 2 thường quá nhỏ: phải gom các khoản cấp 2 liên tiếp |
| Quy định chung | Trộn khoản cho Người dùng và cho Đối tác | Cần nhãn `doi_tuong` theo khoản |
| 15 Phụ lục của Điều khoản sử dụng | Chưa đo (phát hiện 2026-09-22, xem trên); độ dài dao động mạnh — nhỏ nhất 997 ký tự (Phụ lục 13), lớn nhất 16.319 ký tự (Phụ lục 8) | Đo trước khi chốt ngân sách chunk; nhiều khả năng cũng cần gom/tách như Quy định chung |
| Quy chế hoạt động | 56 ảnh, chưa biết cấu trúc | Quyết định sau khi OCR |
| Bảo hiểm, Chính sách dữ liệu | Có bảng | Xử lý bảng riêng |

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Cách chunk | Theo cấu trúc, mỗi nhóm tài liệu một quy tắc (bảng dưới) | Khung đánh số và cặp hỏi–đáp đã cho sẵn ranh giới |
| Ngữ cảnh | Breadcrumb `Văn bản › mục › khoản` đặt đầu text được embed và BM25 | Miễn phí, xác định, không cần LLM |
| Chunk id | `<tài liệu>#<số>`, ví dụ `general#3.2`, `faq#3.6`; chunk gom nhiều khoản ghi khoảng `general#3.2-3.4` | Citation và re-index không vỡ |
| Đối tượng | Nhãn `doi_tuong` theo khoản (`nguoi_dung`, `doi_tac`, `chung`); truy hồi cho khách chỉ lấy `nguoi_dung` và `chung` | Định nghĩa và điều khoản chung vẫn còn; đảo ngược được |
| Ngân sách | ~500 token theo tokenizer của model embedding, chỉnh bằng eval | Số cuối chốt sau Bước 3 |
| Baseline | Cửa sổ 500 token, overlap 10% | Để so trên eval (Bước 9) |
| LLM sinh ngữ cảnh | Thử sau, A/B trong eval | Cần baseline breadcrumb để biết LLM có giúp thật không |

## Quy tắc theo nhóm

| Nhóm | Đơn vị chunk | Chi tiết |
|---|---|---|
| FAQ | 1 câu hỏi + trả lời | Text: câu hỏi rồi trả lời; giữ các bước đánh số cùng chunk; breadcrumb `Trung tâm giải đáp › <nhóm> › <số>. <câu hỏi>`; bỏ ảnh minh họa; cặp vượt ngân sách (2/49) tách theo "Bước N" |
| Điều khoản, chính sách | Mục cấp 1 nếu vừa ngân sách; nếu dài thì gom các khoản cấp 2 liên tiếp | Không cắt ngang khoản; khoản quá dài mới tách cấp 3, `(i)` hoặc gạch đầu dòng; mỗi chunk lặp tiêu đề mục cấp 1; **không gom khoản khác `doi_tuong` vào một chunk** |
| Quy chế (ảnh OCR) | Như điều khoản nếu có đánh số, không thì theo đoạn | Nối câu và khoản vắt qua ngắt trang; giữ `trang_bat_dau`, `trang_ket_thuc` |
| Bảng | Cả bảng nếu nhỏ, không thì theo nhóm hàng và lặp dòng tiêu đề | Giữ bảng Markdown để hiển thị; thêm bản viết từng hàng thành câu để embed và BM25 |

## Metadata mỗi chunk

`chunk_id`, `parent_id` (mục cấp 1, ví dụ `general#3`), `doc_id`, `doc_type` (`faq`, `dieu_khoan`, `chinh_sach`, `quy_che`, `bao_hiem`), `heading_path`, `so_muc`, `doi_tuong`, `audience`, `nguon_tin_cay`, `ngay_hieu_luc`, `trang_bat_dau`, `trang_ket_thuc`, `loai_chunk` (`faq`, `dieu_khoan`, `bang`, `generic`), `source`, `token_count`.

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| Cửa sổ cố định làm chính | Cắt ngang khoản và chuỗi bước | Vẫn giữ làm baseline |
| Recursive splitter làm chính | Mù số thứ tự | Chỉ dùng dự phòng (OCR không có cấu trúc) |
| Parent-child hai tầng | Hai tầng, khó eval; đã lưu `parent_id` | Eval cho thấy chunk khoản thiếu ngữ cảnh |
| Semantic chunking | Tốn, biên không khớp khung đánh số sẵn có, id không ổn định | Hiếm khi cần |
| Proposition/agentic (LLM tách mệnh đề) | Diễn đạt lại làm sai câu chữ chính sách | — |
| Late chunking | Cần model long-context, phức tạp | — |
| Bỏ khoản của Đối tác khi ingest | Mất ngữ cảnh, phải chunk lại nếu mở rộng đối tượng | Nếu chắc không bao giờ mở rộng cho tài xế |
| Không gắn nhãn đối tượng | Trả lời khách bằng quy định dành cho đối tác | — |
| Contextual Retrieval bằng LLM ngay | Không có baseline để so; thêm bước phải kiểm tra | Thử ở eval: corpus chỉ vài trăm chunk và dữ liệu công khai nên rẻ |

## Rủi ro và kiểm chứng

- Regex nhận `doi_tuong` dựa vào cụm như "Đối với Đối Tác", "Nếu Bạn là Người dùng"; khoản không có cụm nào nhận là `chung`. Kiểm tra tay vài chục khoản.
- Nhận đúng mục cấp 1 (tiêu đề in hoa sau `N.`); đếm số mục liên tục 1..N để bắt lỗi, kể cả lỗi OCR.
- Chưa xem bảng thật của Bảo hiểm và Chính sách dữ liệu; chốt cách viết lại hàng sau khi xem.
- Ngân sách token chỉ là điểm xuất phát.

## Bài học

- Số đo thật sửa ước lượng: mục cấp 1 trung vị 418 token nhưng đuôi dài tới 3,4k; khối cấp 2 trung vị chỉ 66 token. Gom khoản cấp 2 là cần thiết, không phải tùy chọn.
- 500 token ≈ 400 từ tiếng Việt với tokenizer XLM-R (1,26 token/từ), ≈ 370 từ với Qwen3 (1,36).
- Ranh giới chunk tốt nhất là ranh giới tài liệu đã có: số thứ tự, cặp hỏi–đáp.
- Một văn bản có thể phục vụ nhiều đối tượng: gắn nhãn thay vì cắt bỏ, và đừng gom khoản khác nhãn vào một chunk.
- Thí nghiệm với LLM chỉ đáng khi corpus nhỏ và dữ liệu công khai: bắt đầu bằng phương án miễn phí rồi đo.

## Tham khảo

- Contextual Retrieval (Anthropic): https://www.anthropic.com/engineering/contextual-retrieval
