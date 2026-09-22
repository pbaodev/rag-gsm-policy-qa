# Bước 6: PageIndex fallback

Corpus: chính sách GSM tiếng Việt, ~68–74 nghìn token text (Bước 3, sửa 2026-09-22), ước lượng 300–600 chunk sau khi gom/tách (576 dòng tiêu đề thô đếm được sau ingest — số chunk thật sẽ khác vì Bước 2 gom khoản cấp 2 nhỏ và tách khoản cấp 3 quá dài), mỗi chunk đã có `heading_path`, `parent_id`, breadcrumb (Bước 2). Bước này chỉ chạy khi nhánh hybrid (Bước 5) không đạt ngưỡng.

## Sơ đồ (đã chốt ở Bước 0)

```
... → Rerank → top-1 < ngưỡng
                  → PageIndex fallback → đủ bằng chứng?
                        có    → Context reorder
                        không → "Không biết"
```

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Kiến trúc | **Tự viết**, không dùng thư viện `pageindex` (VectifyAI) | Tái dùng cây heading + breadcrumb đã dựng ở Bước 1–2; thư viện này mặc định tự trích lại cấu trúc tài liệu bằng LLM và cần `OPENAI_API_KEY` — việc ta đã làm miễn phí lúc ingest, và không khớp adapter Claude/Ollama đã chốt ở Bước 0 |
| Cách tìm | **Single-pass**: một lượt gọi LLM với toàn bộ outline (đã lọc audience), không đệ quy nhiều vòng | Outline ước tính vài chục nghìn token (sửa 2026-09-22: ban đầu tưởng "vài nghìn", corpus thật lớn hơn — xem trên) — vẫn nằm gọn một lượt gọi Claude (200k+ token), nhưng **gần như chắc chắn** cần tăng `num_ctx` khi chạy qua Ollama, không còn là rủi ro "có thể" như bản trước; tránh độ phức tạp đệ quy/MCTS mà chính PageIndex cũng chưa công bố chi tiết ở bản production |
| Nội dung mỗi node | Breadcrumb (Bước 2) + trích N ký tự đầu chunk | (bạn chọn) Breadcrumb bị lặp giữa các khoản cùng mục cấp 1 (khoản cấp 2 thường không có tiêu đề riêng, chỉ đánh số — Bước 2); trích đoạn thêm tín hiệu nội dung mà không cần LLM tóm tắt lúc index, giữ đúng nguyên tắc "cây dựng không cần LLM" của PageIndex |
| Model chạy | `qwen3:4b` local, thử trước | (bạn chọn) Đúng chiến lược hybrid Bước 0 (mặc định local, đổi khi đo thấy yếu); Bước 0 đã ghi sẵn dự đoán đổi sang Claude nếu bước này yếu |
| Đầu ra LLM | JSON `{reasoning, node_list}`, theo đúng format cơ bản của PageIndex | Format đã được bên ngoài kiểm chứng, dễ parse, dễ hiện trong trace panel (Bước 8) |
| Tiêu chí "đủ bằng chứng" | `node_list` khác rỗng **và** LLM trích được câu nguyên văn từ chunk đã chọn (grounding) | Trả lời sai chính sách cho khách nguy hiểm hơn "không biết"; bắt trích nguyên văn buộc LLM bám chunk thật thay vì bịa |
| Phạm vi lọc | Cùng bộ lọc `doi_tuong`/`audience` như nhánh hybrid, áp trước khi dựng outline | Nhất quán với Bước 4–5; không rò điều khoản đối tác hay tài liệu nội bộ qua đường vòng |

## Định dạng

```
Outline entry : {chunk_id, breadcrumb, doan_trich}      # doan_trich = N ký tự đầu chunk
Prompt        : outline toàn bộ (đã lọc audience) + câu hỏi
Output LLM    : {"reasoning": "...", "node_list": [{"chunk_id": "faq#3.6", "trich_dan": "..."}]}
```

`node_list` rỗng, hoặc `trich_dan` không khớp nội dung thật của `chunk_id` (kiểm bằng so chuỗi con) → coi như không đủ bằng chứng, đi nhánh "không biết".

## So sánh với thư viện PageIndex (VectifyAI)

| Phương án | Ưu | Nhược | Quyết định |
|---|---|---|---|
| Thư viện `pageindex` (MIT, ~35,8k sao, Python) | Thuật toán đã kiểm chứng — 98,7% trên FinanceBench so với ~30–50% của RAG vector thường; định dạng JSON tree + reasoning có sẵn | Quickstart mặc định cần `OPENAI_API_KEY`; tự trích cấu trúc tài liệu bằng LLM lúc index — trùng việc ingest/chunking đã làm miễn phí; MCTS bản "sản xuất" chưa công bố chi tiết | Không chọn, dùng làm tham khảo thuật toán |
| Tự viết, tái dùng cây + breadcrumb có sẵn | Không tính lại cấu trúc; không phụ thuộc OpenAI; khớp thẳng adapter LLM đã có (Bước 0) | Tự lo prompt, parse JSON, xử lý lỗi định dạng | **Chọn** |

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| Dùng thư viện `pageindex` | Cần `OPENAI_API_KEY`, tự trích lại cấu trúc tài liệu bằng LLM dù ta đã có cây từ ingest; thêm phụ thuộc ngoài "tự viết lõi" đã chốt ở Bước 0.3 | Nếu sau này cần đọc tài liệu dài, không có cấu trúc sẵn (không phải trường hợp GSM) |
| Đệ quy nhiều vòng theo từng cấp cây (top-down, kiểu MCTS) | Outline toàn bộ ước tính vài chục nghìn token (sửa 2026-09-22), vẫn một lượt là đủ với Claude; đệ quy thêm độ trễ và độ phức tạp không cần thiết ở quy mô này | Nếu corpus lớn hơn nhiều (hàng nghìn tài liệu) khiến outline không còn vừa một lượt gọi kể cả với Claude |
| Chỉ breadcrumb, không trích đoạn | Khoản cấp 2 không có tiêu đề riêng nên nhiều chunk trùng breadcrumb, LLM khó phân biệt | Nếu sau này gắn tiêu đề tự động cho khoản cấp 2 |
| Bỏ cây, nhét toàn bộ corpus liên quan vào 1 prompt | Khả thi về mặt cửa sổ ngữ cảnh (68–74 nghìn token, sửa 2026-09-22 — vẫn nhỏ hơn corpus tưởng ban đầu là lớn hơn) nhưng tốn token/độ trễ mỗi lần fallback hơn hẳn một outline vài chục nghìn token; ý tưởng này đã có chỗ riêng — baseline "nhét hết" ở Bước 9 để so cả hệ thống, không phải để thay nhánh fallback | Nếu outline + trích đoạn vẫn cho kết quả tệ trên eval, thử full-context như một bậc dự phòng thứ hai trước khi trả "không biết" |
| Claude ngay từ đầu cho fallback | Thử local trước theo đúng chiến lược hybrid; đo trên eval Bước 9 rồi mới đổi | Nếu `qwen3:4b` ra JSON sai định dạng thường xuyên hoặc chọn sai node rõ rệt |

## Rủi ro và kiểm chứng

- Chưa đo `qwen3:4b` (qua Ollama) có tuân theo định dạng JSON `{reasoning, node_list}` ổn định không — model nhỏ dễ lệch format; cần thử vài chục câu trước khi tin tưởng.
- Grounding check (bắt trích nguyên văn) chỉ giảm rủi ro bịa, không loại bỏ hoàn toàn — eval Bước 9 cần có câu hỏi cố tình đánh lừa (không có trong corpus) để đo tỉ lệ "không biết" đúng/sai.
- Outline ước tính vài chục nghìn token (sửa 2026-09-22) gần chắc chắn **vượt** cửa sổ ngữ cảnh mặc định của Ollama (thường 2–4k trừ khi tự tăng `num_ctx`) — không còn là "có thể", phải tăng `num_ctx` khi cài, hoặc excerpt phải ngắn lại đáng kể, hoặc lọc bớt tài liệu trước khi dựng outline (theo chủ đề/`doc_type`) thay vì luôn đưa toàn bộ corpus khách hàng vào một outline.
- Độ dài trích đoạn (N ký tự đầu chunk) chưa chốt số — cần thử trên vài chục chunk điều khoản: đoạn đầu có mang đủ tín hiệu hay chỉ chung chung (ví dụ mở đầu bằng "Trường hợp...", không lộ chủ đề).
- Nhánh này chỉ chạy sau khi hybrid + rerank thất bại: bộ câu hỏi eval (Bước 9) cần có nhóm câu hỏi cố tình khó cho dense/BM25 (từ đồng nghĩa, diễn đạt xa tiêu đề) để nhánh thực sự được đo, không chỉ nằm im trong sơ đồ.

## Bài học

- PageIndex "gốc" build cây bằng LLM vì không kiểm soát được cấu trúc tài liệu đầu vào (PDF bất kỳ); ta kiểm soát được (đã tự dựng heading ở Bước 1) nên phần tốn kém nhất của kỹ thuật này không áp dụng — lặp lại bài học Bước 1: "Heading là hợp đồng giữa ingest, PageIndex và citation".
- Thuật toán "tree search" cơ bản của PageIndex chỉ là một lượt gọi LLM với toàn bộ outline; phần MCTS phức tạp là tính năng sản phẩm đóng, chưa công bố chi tiết — không cần đuổi theo độ phức tạp không cần thiết cho corpus vài trăm chunk.
- Rủi ro lớn nhất của nhánh này không phải "không tìm thấy" mà là "tìm sai và trả lời sai": nhánh "không biết" có mặt trong sơ đồ từ Bước 0 chính vì lý do này; bắt LLM trích nguyên văn là một cách rẻ để giảm rủi ro đó.
- **(2026-09-22)** Kiến trúc (single-pass, một lượt gọi) vẫn đúng sau khi corpus thật lớn hơn ước lượng ~1,7 lần — nhưng con số cụ thể đổi hẳn ý nghĩa thực tế: "vài nghìn token, chạy đâu cũng được" trở thành "vài chục nghìn token, gần như bắt buộc cấu hình lại Ollama". Một quyết định kiến trúc có thể đứng vững trong khi giả định số liệu bên dưới nó sai hoàn toàn — phải tách hai việc này ra khi soát lại tài liệu.

## Tham khảo

- PageIndex (VectifyAI, MIT): https://github.com/VectifyAI/PageIndex
- LLM Tree Search (tài liệu chính thức): https://docs.pageindex.ai/tutorials/tree-search/llm
- Kết quả FinanceBench: https://venturebeat.com/infrastructure/this-tree-search-framework-hits-98-7-on-documents-where-vector-search-fails
