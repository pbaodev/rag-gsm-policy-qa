# Capability Map: Mini RAG Pipeline (tiếng Việt)

Trạng thái: **đã duyệt** 2026-09-21. Cập nhật 2026-09-21: đổi miền từ pháp luật hộ kinh doanh sang chính sách GSM; đã kiểm kê nguồn greensm.com. Cập nhật 2026-09-22 (sáng): bắt đầu code `ingest`; kiểm kê lại greensm.com bằng dữ liệu thật thay vì HTML tĩnh — hầu hết nội dung nằm trong `__NEXT_DATA__` (JSON), không phải DOM; corpus thật ~70 nghìn token (trước ước lượng ~40 nghìn) — sửa `01-ingestion.md`, `02-chunking.md`, `03-embedding.md`, `06-pageindex-fallback.md`. Cập nhật 2026-09-22 (chiều): code `chunk`, chạy trên 18 tài liệu thật ra 337 chunk; sửa lỗi gán `doi_tuong` theo đoạn văn cho tài liệu không có heading; số đo median/p90 trong `02-chunking.md` được thay bằng số thật. Cập nhật 2026-09-22 (tối): code `index` (embedder bge-m3, LanceDB, bm25s), tạo `config/default.toml` + `rag_gsm/config.py` thật; dựng xong `index/public/{lancedb,bm25}/` từ 337 chunk; kiểm tra tay khớp đúng ca hòa điểm đã ghi ở `04-index.md`.

| Module id | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `ingest` | Collect/crawl + convert → Markdown | — |
| `index` | Chunk, embed, dense store, BM25 | ingest |
| `retrieve` | Hybrid RRF, [rerank], fallback PageIndex, context reorder | index |
| `generate` | Prompt, LLM, citation, nhánh "không biết" | retrieve |
| `ui` | Streamlit chat + trace panel | generate |
| `eval` | Bộ câu hỏi vàng; đo retrieval và answer | retrieve, generate |

Thứ tự build: ingest → index → retrieve → generate → ui.
Bộ câu hỏi eval soạn sớm, chạy lại sau mỗi module.
Kiến trúc code (cấu trúc thư mục, interface, config) trước khi build: [kien-truc-code.md](docs/kien-truc-code.md).

## Quyết định nền (mọi module tuân theo)

- **Corpus:** tiếng Việt, chính sách GSM (Green SM) cho khách hàng đi xe: đặt xe, thay đổi chuyến, giá và thanh toán, hoàn tiền, khiếu nại và CSKH, đồ thất lạc, security, privacy, FAQ, SLA, RBAC. Nguồn: greensm.com, thông tin crawl thêm (có nhãn tin cậy), tài liệu nội bộ bổ sung sau
- **Người dùng:** một vai trò, khách hàng đi xe. RBAC chỉ là chủ đề tài liệu. Tài liệu nội bộ (nếu thêm sau) gắn `audience=noi_bo`, index tách riêng, không bao giờ trả cho khách
- **Model:** hybrid — embedding chạy local; LLM qua adapter (Ollama `qwen3:4b` khi dev, Claude API khi cần chất lượng). Tài liệu công khai nên giữ hybrid. Embedding mặc định: bge-m3 qua sentence-transformers; chốt cuối bằng bake-off trên eval, có thêm 1 mốc API
- **Cách build:** tự viết lõi (RRF, ngưỡng fallback, reorder, citation); dùng thư viện cho parser / embedding / vector store; không dùng LangChain hay LlamaIndex
- **Index:** LanceDB (dense, cosine, quét phẳng) + bm25s (BM25, âm tiết bỏ dấu, một chỉ mục); index public và internal tách hẳn thư mục
- **Môi trường:** `uv` + Python 3.12, chạy local (Mac arm64, 16 GB)
- **Phiên bản tài liệu:** MVP chỉ giữ bản hiện hành; ghi `fetched_at` và `ngay_hieu_luc` nếu trang có (Quy định chung: 07/08/2026; Chính sách dữ liệu cá nhân: 31/07/2026). Đây là giả định, chờ xác nhận

## Tiến độ brainstorm → tài liệu học

| Bước | Trạng thái | File |
|---|---|---|
| 0 Nền móng | xong | [00-nen-mong.md](docs/learning/00-nen-mong.md) |
| 1 Ingestion (collect + convert) | xong; sửa lớn 2026-09-22 (JSON thay DOM); tin tức tính sau | [01-ingestion.md](docs/learning/01-ingestion.md) |
| 2 Chunking | xong; code thật 2026-09-22, số đo thay bằng số thật (337 chunk/18 tài liệu) | [02-chunking.md](docs/learning/02-chunking.md) |
| 3 Embedding | xong | [03-embedding.md](docs/learning/03-embedding.md) |
| 4 Index (vector store + BM25) | xong; code thật 2026-09-22, dựng từ 337 chunk thật | [04-index.md](docs/learning/04-index.md) |
| 5 Retrieval (hybrid, RRF, rerank) | xong | [05-retrieval.md](docs/learning/05-retrieval.md) |
| 6 Fallback PageIndex | xong | [06-pageindex-fallback.md](docs/learning/06-pageindex-fallback.md) |
| 7 Reorder + Generation + Citation | xong | [07-reorder-generation-citation.md](docs/learning/07-reorder-generation-citation.md) |
| 8 Streamlit UI | xong | [08-streamlit-ui.md](docs/learning/08-streamlit-ui.md) |
| 9 Eval | xong | [09-eval.md](docs/learning/09-eval.md) |
