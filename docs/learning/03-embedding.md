# Bước 3: Embedding

Corpus: chính sách GSM tiếng Việt, phần text khoảng 68–74 nghìn token (đo thật sau khi ingest xong 18 tài liệu JSON — 54.232 từ, quy đổi theo tỷ lệ XLM-R/Qwen3 bên dưới; chưa tính Quy chế OCR). **Sửa 2026-09-22:** con số này lúc brainstorm ước lượng ~40 nghìn token, dựa trên hiểu nhầm "Quy định chung" chỉ là 1 văn bản — thực ra là 16 (xem `01-ingestion.md`), nên corpus thật lớn hơn ước lượng ban đầu khoảng 1,7 lần. Không đổi quyết định nào ở bước này (limit token của các model ứng viên đều ≥ 512 mỗi chunk, không phải cả corpus), chỉ đổi ước lượng tổng và bảng "Baseline nhét hết vào context" bên dưới. Embedding chạy local (quyết định Bước 0).

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Model mặc định | **bge-m3** (MIT, 568M, 1024 chiều, 8192 token) | Không cần prefix; không rủi ro cắt im lặng ở cỡ chunk của ta; hệ sinh thái ổn định (37 triệu lượt tải/30 ngày, không đổi từ 2024); còn sparse và multi-vector để thử sau |
| Cách chạy | **sentence-transformers** (PyTorch, MPS) | Có tokenizer của chính model để đếm token chunk; điều khiển được prefix và instruction. Ollama chỉ dùng cho LLM |
| Interface | `Embedder` với `embed_documents` và `embed_query` | Mỗi model xử lý câu hỏi và tài liệu khác nhau; cho phép hoán đổi để bake-off |
| Chốt model cuối | Bake-off trên eval GSM (Bước 9), không theo benchmark | Benchmark dịch máy và lệch miền |
| Mốc trần | Thêm 1 model API vào bake-off | Biết local còn kém trần bao nhiêu |
| Ngưỡng fallback | Hiệu chỉnh lại mỗi khi đổi model | Thang cosine khác nhau giữa các model |

## Ứng viên bake-off

| Model | Giấy phép | Kích thước | Chiều | Token tối đa | Câu hỏi so với tài liệu | VN-MTEB (trung bình) |
|---|---|---|---|---|---|---|
| bge-m3 | MIT | 568M | 1024 | 8192 | Không cần prefix | 64,90 |
| Qwen3-Embedding-0.6B | Apache-2.0 | 596M | 1024 (MRL 32–1024) | 32k | Câu hỏi: `Instruct: <tác vụ>\nQuery:<câu hỏi>`; tài liệu để nguyên | Không có trong bảng |
| gte-multilingual-base | Apache-2.0 | 305M | 768 | 8192 | Kiểm tra khi cài | 65,22 |
| multilingual-e5-large-instruct | MIT | 560M | 1024 | 512 | Câu hỏi có `Instruct:`; kiểm tra khi cài | 67,99 |
| Vietnamese_Embedding (AITeamVN) | Apache-2.0 | 568M | 1024 | 2048 (lúc huấn luyện) | Như bge-m3 | 63,34 |
| Mốc API: `gemini-embedding-2` hoặc `voyage-4-large` | Trả phí, cần key | — | 3072 (giảm được) / 1024 | 8192 / 32k | Gemini: `task: search result \| query: …` cho câu hỏi, `title: … \| text: …` cho tài liệu; Voyage: `input_type` | Không có trong bảng |

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| jina-embeddings v3, v5 | CC-BY-NC-4.0: phi thương mại | Nếu chỉ học và không phát hành |
| Qwen3-Embedding 4B, 8B | Nặng cho 16 GB khi chạy cùng LLM; thừa cho vài trăm chunk | Nếu 0.6B thua rõ trên eval |
| vietnamese-bi-encoder, dangvantuan/vietnamese-embedding | Tối đa 256 token; VN-MTEB 54,89 | — |
| EmbeddingGemma-300m | Bị khóa trên Hugging Face (license Gemma, phải đăng nhập); chưa xác minh tiếng Việt | Thử qua Ollama nếu tò mò |
| nomic-embed-text-v2-moe, snowflake-arctic-embed-l-v2.0 | Chưa có số liệu tiếng Việt | Thêm vào bake-off nếu cần |
| mxbai-embed-large, nomic-embed-text v1.5, all-MiniLM | Tiếng Anh | — |
| multilingual-e5-large (bản thường) | 512 token, cần `query:`/`passage:`, thấp hơn bản instruct (63,87 so với 67,99) | — |
| Ollama làm đường embedding | Ẩn tokenizer, khó đếm token chunk, khó điều khiển prefix; không có e5 và gte | Nếu chỉ cần chạy nhanh |
| bge-m3 sparse hoặc multi-vector thay BM25 | Pipeline đã có BM25 riêng, dễ học và dễ giải thích | Xem lại ở Bước 4–5 |

## Ràng buộc từ số đo

- 500 token ≈ 400 từ tiếng Việt (tokenizer XLM-R), ≈ 370 từ (Qwen3).
- Model 512 token: 2/49 cặp FAQ và 7/87 khối điều khoản đã vượt 512 trước khi thêm breadcrumb và prefix, nên bị cắt im lặng. Model 8192 token trở lên không có rủi ro này ở cỡ chunk của ta.
- Ngưỡng fallback (cosine dense top-1) là thuộc tính của model: đổi model là phải hiệu chỉnh lại.

## Rủi ro và kiểm chứng

- VN-MTEB là bản dịch máy từ MTEB tiếng Anh (41 tập, 18 model). Số liệu tôi đọc qua công cụ tóm tắt, chưa đối chiếu bảng gốc; chênh 1–2 điểm là nhiễu. Bảng không có Qwen3-Embedding và EmbeddingGemma.
- AITeamVN tự đo trên Legal Zalo 2021: Acc@1 0,727 so với 0,568 của bge-m3 gốc; nhưng trên VN-MTEB lại thấp hơn bge-m3. Lợi thế của bản tinh chỉnh phụ thuộc miền.
- Phiên bản: sentence-transformers 6.1.0, transformers 5.17.0, torch 2.14.0 (đều Python ≥ 3.10) là các bản major mới. Kiểm tra API khi cài (`encode_query`, `encode_document`, `prompt_name`).
- Mốc API: chưa có key trong môi trường; giá và gói miễn phí chưa kiểm vì trang docs không nêu.
- Cần bộ câu hỏi eval GSM để bake-off: soạn sớm.

## Baseline nhét hết vào context

Phần text của corpus đo được ~68–74 nghìn token (sửa 2026-09-22, xem trên) — vẫn nhỏ hơn cửa sổ ngữ cảnh của Claude API (200k+ token), nhưng **vượt cửa sổ mặc định của Ollama** (thường 2–4k token trừ khi tự tăng `num_ctx`). Baseline "nhét hết vào prompt" ở Bước 9 vì vậy chỉ khả thi qua Claude, hoặc phải tăng `num_ctx` khi chạy `qwen3:4b` local — không còn "chạy được ngay không cần cấu hình gì" như giả định lúc corpus tưởng chỉ 40 nghìn token. Vẫn nên có baseline này để so với RAG: biết RAG có thật sự hơn không.

## Bài học

- Benchmark chung không thay được eval của mình; benchmark dịch máy càng phải dè dặt.
- Giới hạn token là ràng buộc cứng của model: chunk cộng breadcrumb và prefix phải nằm dưới nó.
- Câu hỏi và tài liệu có thể cần xử lý khác nhau (e5 cần prefix, Qwen3 cần instruction, bge-m3 không): giấu chi tiết đó sau `embed_query` và `embed_documents`.
- Model card mới là nguồn đúng cho prefix và giấy phép, không phải trí nhớ: jina bị loại vì CC-BY-NC.
- Ngưỡng điểm là thuộc tính của model.
- **(2026-09-22)** Ước lượng kích thước corpus trước khi ingest thật dễ sai theo hướng thấp hơn thực tế: "Quy định chung" tưởng 1 văn bản hoá ra 16, corpus tăng ~1,7 lần. May là không đổi quyết định model (limit token tính theo chunk, không theo cả corpus) — nhưng bảng so sánh "vừa cửa sổ ngữ cảnh LLM" thì đổi hẳn kết luận (Ollama mặc định không đủ, Claude thì đủ).

## Tham khảo

- VN-MTEB: https://arxiv.org/abs/2507.21500
- bge-m3: https://huggingface.co/BAAI/bge-m3
- Qwen3-Embedding-0.6B: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- AITeamVN/Vietnamese_Embedding: https://huggingface.co/AITeamVN/Vietnamese_Embedding
- Gemini embeddings: https://ai.google.dev/gemini-api/docs/embeddings
- Voyage embeddings: https://docs.voyageai.com/docs/embeddings
