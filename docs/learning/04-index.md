# Bước 4: Index (vector store + BM25)

Corpus vài trăm đến vài nghìn chunk. Ở quy mô này kho vector không phải nút thắt: quét phẳng 2.000 vector × 1024 chiều mất 3 ms (LanceDB) hoặc 0,2 ms (numpy).

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Kho vector | **LanceDB** 0.39 (embedded, Apache-2.0) | Một thư mục; lọc metadata trước khi xếp hạng; còn cập nhật (09/2026) |
| Cách tìm | Cosine, quét phẳng (chính xác), không ANN | Vài nghìn vector: ANN không có lợi |
| BM25 | **bm25s** 0.3.11 (MIT, chỉ cần numpy) | Tự điều khiển tách từ và k1/b; nhận danh sách token có sẵn; lưu và nạp từ đĩa |
| Tách từ | **Âm tiết bỏ dấu**, một chỉ mục | MRR 0,94 cả khi có dấu lẫn không dấu trong bài thử; bền với câu gõ thiếu dấu một phần |
| Trường BM25 | Văn bản kèm breadcrumb | Tiêu đề mục tham gia khớp từ |
| An toàn | `index/public/` và `index/internal/` tách hẳn | An toàn bằng cấu trúc; bộ lọc `doi_tuong` vẫn áp dụng trước khi xếp hạng |
| Cập nhật | Dựng lại toàn bộ từ danh sách chunk | Vài giây; ingest bỏ qua tài liệu không đổi bằng `content_hash` |
| Kiểm tra | numpy tham chiếu làm test đối chiếu; test "index public không lộ nội bộ" | Bắt lỗi kho và lỗi lọc |

## Layout

```
data/chunks/<doc_id>.jsonl   đầu ra của chunking, đầu vào của index
index/public/lancedb/        bảng chunks: chunk_id, vector, text, text_embed, metadata
index/public/bm25/           chỉ mục bm25s + danh sách chunk_id
index/internal/...           cùng cấu trúc, chỉ khi có tài liệu nội bộ
```

LanceDB trả `_distance` là khoảng cách cosine: độ tương đồng = 1 − `_distance`. Ngưỡng fallback dùng độ tương đồng.

## Bài thử BM25 (161 chunk, 8 câu hỏi, mỗi câu có dấu và không dấu)

| Cách tách từ | Từ vựng | MRR có dấu | MRR không dấu |
|---|---|---|---|
| Âm tiết có dấu | 1.133 | 1,00 | 0,25 |
| **Âm tiết bỏ dấu** | 709 | 0,94 | 0,94 |
| Âm tiết + bigram (có dấu) | 11.112 | 0,92 | 0,28 |
| Âm tiết + bigram (bỏ dấu) | 10.152 | 0,92 | 0,92 |
| underthesea (có dấu) | 1.754 | 1,00 | 0,22 |
| underthesea (bỏ dấu) | 1.647 | 0,94 | 0,79 |
| Subword XLM-R | 1.377 | 1,00 | 0,34 |
| Hai chỉ mục + định tuyến (âm tiết) | — | 1,00 | 0,94 |

Ba điều rút ra: bỏ dấu quyết định kết quả; tách từ không giúp và làm hỏng câu không dấu (bộ tách từ cần dấu để đoán ranh giới); bigram tăng từ vựng gấp 10 mà không hơn.

## Bài thử LanceDB (2.000 vector giả lập)

- Cài và chạy được trên Python 3.12, Mac arm64.
- Lọc **trước**: 5/5 kết quả đúng. Lọc **sau**: chỉ 3. Điều kiện chặt: trước ra 1, sau ra 0.
- Truy vấn 3 ms; numpy thuần 0,2 ms. Lưu và mở lại từ đĩa đúng; 8,3 MB cho 8,2 MB vector thô.

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| numpy thuần + SQLite | Phải tự lo lưu trữ và lọc | Vẫn dùng làm bản đối chiếu trong test |
| Chroma 1.5 | Nặng hơn, HNSW xấp xỉ, không thêm giá trị ở quy mô này | — |
| FAISS 1.15 | Không có metadata; phải ghép kho khác | Khi muốn học các kiểu index (Flat, HNSW, IVF) |
| sqlite-vec 0.1 | Còn 0.x; quét phẳng; nạp extension có thể lỗi trên một số bản Python | Khi muốn một file SQLite duy nhất |
| Qdrant local | Chế độ local thiên về demo; chạy server thì nặng | Khi cần server |
| DuckDB VSS | Thực nghiệm | — |
| Elasticsearch, OpenSearch | Cần server và Java; quá nặng | Khi lên production |
| LanceDB FTS (Tantivy) | Ít điều khiển tách từ, khó chỉnh k1/b, khó đưa điểm vào trace | Nếu muốn một kho duy nhất |
| rank-bm25 | Không cập nhật từ 2022 | — |
| SQLite FTS5 | Bỏ dấu tiếng Việt cần xử lý thêm (chữ đ) | — |
| Âm tiết có dấu | 0,25 khi câu không dấu | — |
| Hai chỉ mục + định tuyến | Tốt nhất trong bài thử (1,00 / 0,94) nhưng thêm chỉ mục; câu có dấu một phần là điểm yếu | Nếu eval cho thấy mất độ chính xác khi có dấu |
| underthesea 9.5 (Apache-2.0) | Không hơn; hỏng câu không dấu; thêm dependency | Nếu eval với câu diễn đạt khác tiêu đề cho thấy có lợi |
| Bigram | Từ vựng gấp 10, không hơn | — |
| Subword XLM-R | 0,34 khi không dấu; buộc BM25 vào tokenizer của model embedding | — |

## Rủi ro và kiểm chứng

- Bài thử chỉ 8 câu sát tiêu đề FAQ: chỉ thấy hiệu ứng lớn như dấu, không kết luận được về tách từ. Eval Bước 9 phải có câu không dấu, dấu một phần và diễn đạt khác tiêu đề.
- Bỏ dấu gây nhập nhằng (ví dụ "hủy" và "huy"). Dense và rerank bù; theo dõi trong eval.
- Ca hòa điểm: với câu "hủy chuyến xe có bị trừ tiền không", FAQ 3.6 được 7,78, sát FAQ 2.16 được 7,74. Đây là chỗ dense và rerank cần giúp.
- LanceDB còn 0.x, API còn đổi: ghim phiên bản và luôn truyền `prefilter` tường minh.
- Chưa thử: stopwords, k1 và b, trọng số trường tiêu đề.

## Bài học

- Ở quy mô nhỏ, chọn kho vector theo lọc, lưu trữ và độ đơn giản, không theo tốc độ.
- Lọc trước khi xếp hạng: lọc sau có thể trả thiếu hoặc không trả gì.
- An toàn bằng cấu trúc (index tách riêng), không chỉ bằng bộ lọc.
- Tiếng Việt chuẩn hóa hai lần: NFC ở ingest, bỏ dấu ở BM25.
- Benchmark độ chính xác tách từ không phải benchmark truy hồi; không tìm thấy bằng chứng công khai về việc tách từ giúp BM25 tiếng Việt, nên phải tự đo.
- Bài thử nhỏ vẫn có ích khi hiệu ứng đủ lớn, miễn là nói rõ nó không chứng minh được gì hơn.

## Tham khảo

- LanceDB Full-Text Search: https://docs.lancedb.com/search/full-text-search
- bm25s: https://github.com/xhluca/bm25s
