# Bước 0: Nền móng

## Luồng đã chỉnh (`(+)` = thêm so với bản gốc)

```
[Index]  Docs/Web → Collect → Markdown → Chunk → Dense index + BM25 index
[Query]  Dense ∥ BM25 → RRF → (+)Rerank → top-1 ≥ ngưỡng?
           có    → Context reorder
           không → PageIndex fallback → đủ bằng chứng?
                      có    → Context reorder
                      không → (+)"Không biết"
         Context reorder → LLM → Answer + Citation → Streamlit (+trace panel)
[(+)Eval] Bộ câu hỏi vàng, chạy lại sau mỗi module
```

## 0.1 Ngôn ngữ corpus: tiếng Việt

**Chọn:** tiếng Việt, vì đúng nhu cầu thật và học được nhiều nhất.

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| Tiếng Việt | Đúng nhu cầu; học cả tách từ lẫn embedding | Ít model và tài nguyên hơn tiếng Anh | **Chọn** |
| Tiếng Anh | Dễ nhất, model sẵn | Né mất bài toán thật | Không chọn |
| Song ngữ | Sát thực tế | Hai tokenizer, eval phức tạp gấp đôi | Không chọn |

**Hệ quả:**
- Embedding phải hỗ trợ tiếng Việt (Bước 3).
- BM25 cần tách từ, vì một từ tiếng Việt thường gồm nhiều âm tiết (Bước 4).
- LLM local 3–4B trả lời tiếng Việt yếu hơn tiếng Anh.

## 0.2 Model: hybrid

**Chọn:** embedding chạy local, LLM đi qua adapter mỏng.

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| Hybrid | Embedding miễn phí, tái lập; đổi LLM bằng config | Phải viết 1 lớp adapter | **Chọn** |
| Full local | Miễn phí, riêng tư | 4B trên 16 GB: generation và PageIndex yếu, chậm | Không chọn |
| Full API | Chất lượng cao, đơn giản | Tốn phí, cần key, phụ thuộc mạng | Không chọn |

**Khi nào đổi:** embedding local không đạt trên eval (Bước 9) → thử embedding API. PageIndex bằng model local quá yếu → dùng Claude riêng cho bước đó.

**Xác nhận lại (miền GSM):** tài liệu công khai, không nhạy cảm, nên giữ Hybrid. Nếu sau này thêm tài liệu nội bộ, nội dung nội bộ chỉ đi qua model local.

## 0.3 Cách build: tự viết lõi

**Chọn:** tự viết RRF, ngưỡng fallback, context reorder, ghép prompt + citation. Dùng thư viện cho parser, embedding, vector store, BM25.

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| Tự viết lõi + thư viện phần phụ | Thấy rõ từng bước, ít phụ thuộc | Tốn công hơn framework | **Chọn** |
| Framework (LlamaIndex, LangChain) | Nhanh, nhiều tích hợp | Che chi tiết, API đổi nhanh | Không chọn |
| Tự viết gần hết | Học tối đa | Tốn thời gian ở phần không phải RAG | Không chọn |

## Bài học

- Điểm RRF là điểm theo *hạng*, không so được với cosine → không đặt ngưỡng lên RRF.
- Mọi tham số (chunk size, k, ngưỡng) phải có eval đo, không đoán.
