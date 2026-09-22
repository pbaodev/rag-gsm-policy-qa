# Bước 5: Retrieval (hybrid, RRF, rerank)

Corpus: chính sách GSM tiếng Việt, index đã có ở Bước 4 (LanceDB dense + bm25s). Bước này gộp hai nhánh truy hồi và tinh lọc lại bằng reranker trước khi đưa vào ngưỡng fallback.

## Sơ đồ (đã chốt ở Bước 0)

```
Dense ∥ BM25 → RRF → Rerank → top-1 (điểm rerank) ≥ ngưỡng?
```

Ngưỡng đứng trên **điểm rerank**, không phải điểm RRF (điểm theo hạng, không so được với cosine — bài học Bước 0) và không phải cosine thô (đã bị rerank ghi đè thứ tự).

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Công thức gộp | **RRF**: `score(d) = Σ 1/(k + rank_i(d))`, k=60 | Chuẩn gốc (Cormack, Clarke, Büttcher 2009), không cần chuẩn hoá thang điểm giữa cosine và BM25; k=60 là hằng số thực nghiệm của chính bài báo, dùng làm điểm khởi đầu |
| Độ sâu trước khi gộp | Top-20 mỗi nhánh (dense, BM25) | Đủ rộng để không bỏ sót ứng viên đúng trước khi rerank tinh; corpus vài trăm–vài nghìn chunk nên rẻ. Số khởi đầu, chỉnh bằng eval |
| Trọng số RRF | **Không trọng số** (hai nhánh bằng nhau) | RRF gốc không trọng số; ít tham số phải đoán trước khi có baseline để so. Thêm trọng số sau nếu eval cho thấy một nhánh nên mạnh hơn |
| Model rerank mặc định | **AITeamVN/Vietnamese_Reranker** (Apache-2.0, 0,6B, tinh chỉnh từ bge-reranker-v2-m3) | Tinh chỉnh tiếng Việt trên 1,1 triệu triplet; max 2304 token (256 câu hỏi + 2048 văn bản) — vượt hẳn cỡ chunk ~500 token của ta, không rủi ro cắt |
| Cách chạy | **sentence-transformers `CrossEncoder`** | Đã có sentence-transformers trong stack từ Bước 3; model cùng đầu `AutoModelForSequenceClassification` như bge-reranker-v2-m3 nên tải thẳng, không thêm dependency mới |
| Số ứng viên vào rerank | Top-10 sau RRF | Cross-encoder tốn hơn embedding nhiều lần (chạy từng cặp câu hỏi–chunk); corpus nhỏ nên 10 đủ. Số khởi đầu, chỉnh bằng eval |
| Chuẩn hoá điểm rerank | Sigmoid → [0, 1] | Điểm thô của reranker họ BGE không có thang cố định; ngưỡng fallback cần một thang so sánh được, giống lý do ngưỡng dense phải hiệu chỉnh theo model ở Bước 3 |
| Mốc trần API (reranker) | **Không thêm** | Corpus nhỏ, chưa có API key trong môi trường; Bước 3 đã có mốc trần riêng cho embedding, không cần thêm ở bước này |

## Ứng viên reranker (đã kiểm kê)

| Model | Giấy phép | Kích thước | Token tối đa | Ghi chú |
|---|---|---|---|---|
| **AITeamVN/Vietnamese_Reranker** | Apache-2.0 | 0,6B | 2304 (256 + 2048) | Tinh chỉnh từ bge-reranker-v2-m3; tự đo trên Legal Zalo 2021: Acc@1 0,7944 so với 0,5682 của bge-reranker-v2-m3 gốc |
| BAAI/bge-reranker-v2-m3 | Apache-2.0 | 568M (nền bge-m3) | Model card ghi 8192; ví dụ code dùng `max_length=512` | Bản gốc chưa tinh chỉnh; `normalize=True` để có sigmoid sẵn (thư viện FlagEmbedding) |
| Qwen3-Reranker-0.6B | Apache-2.0 | 0,6B | 32k | Cùng họ Qwen3-Embedding; cần prompt `Instruct: …\nQuery: …`; không phải seq-classification thường (lấy logit token yes/no), trừ khi dùng checkpoint đã chuyển đổi |
| namdp-ptit/ViRanker | Apache-2.0 | 0,6B (nền bge-m3) | 512 | Tinh chỉnh tiếng Việt khác (nghiên cứu, arXiv 2509.09131); tự đo trên MS MARCO Vietnamese dev: NDCG@10 0,73 so với bge-reranker-v2-m3 0,6872 |
| jina-reranker-v2-base-multilingual | CC-BY-NC-4.0 | — | — | Phi thương mại |
| mixedbread mxbai-rerank-v2 (base/large) | Apache-2.0 | — | — | "100+ ngôn ngữ", mạnh Anh/Trung; chưa có bằng chứng tiếng Việt cụ thể |
| Mốc API: Cohere Rerank v3.5 | Trả phí | — | hỗ trợ tiếng Việt (mã `vi`) | Có API key trial miễn phí; giá theo lượt tìm chưa xác nhận được số chính xác (nguồn mâu thuẫn ~$1–2/1k lượt) |
| Mốc API: Voyage rerank-2.5 | Trả phí | — | 32k, đa ngôn ngữ (51 tập/31 ngôn ngữ) | 200 triệu token đầu miễn phí/tài khoản, sau đó $0,05/1M token |

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| BAAI/bge-reranker-v2-m3 (bản gốc) | Bản tinh chỉnh tiếng Việt đo cao hơn hẳn trên Legal Zalo, nhưng đây là số tự công bố của AITeamVN, miền pháp luật khác GSM | Nếu eval GSM cho thấy bản tinh chỉnh kém hơn bản gốc (overfit miền pháp luật) |
| Qwen3-Reranker-0.6B | Chưa có bằng chứng tiếng Việt riêng; cần prompt instruction và xử lý logit riêng thay vì seq-classification thường | Nếu Bước 3 chọn Qwen3-Embedding và muốn cùng họ model, hoặc nếu AITeamVN kém trên eval |
| namdp-ptit/ViRanker | Max 512 token: cùng rủi ro cắt im lặng đã thấy ở Bước 3 (7/87 khối điều khoản vượt 512 trước breadcrumb); benchmark tự đo (MS MARCO VN dịch) không so trực tiếp được với AITeamVN (khác tập đo) | Nếu chunk luôn dưới 512 token sau breadcrumb thì rủi ro cắt không còn quan trọng |
| jina-reranker-v2-base-multilingual | CC-BY-NC-4.0, cùng lý do loại jina embedding ở Bước 3 | Nếu chỉ học và không phát hành |
| mixedbread mxbai-rerank-v2 | Apache-2.0 nhưng chưa xác nhận tiếng Việt | Nếu các ứng viên trên đều yếu trên eval GSM |
| Mốc trần API (Cohere / Voyage) cho rerank | Bạn chọn chưa thêm; corpus nhỏ, chưa có key | Nếu bake-off local không đạt, hoặc muốn biết trần chất lượng |
| Weighted RRF (trọng số riêng theo nhánh) | Bạn chọn bắt đầu không trọng số cho đơn giản; thêm tham số phải tune trước khi có baseline để so | Nếu eval cho thấy một nhánh (dense hoặc BM25) nên mạnh hơn hẳn nhánh kia |
| Gộp theo điểm thô (chuẩn hoá min-max cosine + BM25 rồi cộng) | Cosine và điểm BM25 khác thang, chuẩn hoá không ổn định giữa các câu hỏi; RRF chỉ cần thứ hạng (bài học Bước 0) | Nếu RRF cho kết quả tệ hơn rõ rệt so với chuẩn hoá điểm trên eval |

## Rủi ro và kiểm chứng

- AITeamVN/Vietnamese_Reranker tự đo trên Legal Zalo 2021 (miền pháp luật), không phải GSM: số liệu chỉ có tính tham khảo, phải đo lại trên eval GSM (Bước 9), giống cảnh báo đã ghi cho AITeamVN/Vietnamese_Embedding ở Bước 3.
- Hai bản tinh chỉnh tiếng Việt (AITeamVN, ViRanker) đo trên hai benchmark khác nhau (Legal Zalo vs MS MARCO VN dịch): không so trực tiếp được với nhau, chỉ so được với cùng baseline (bge-reranker-v2-m3) trong bài đo của chính mỗi bên.
- Chưa đo latency thật của cross-encoder trên máy 16 GB khi chạy song song với LLM local (`qwen3:4b`) — cross-encoder tốn hơn embedding nhiều lần vì chạy từng cặp câu hỏi–chunk; cần đo trước khi chốt top-N vào rerank.
- Chưa xác nhận `sentence-transformers.CrossEncoder` tải thẳng được AITeamVN/Vietnamese_Reranker không lỗi — suy luận từ việc nó dùng cùng đầu `AutoModelForSequenceClassification` như bge-reranker-v2-m3, cần thử khi cài.
- k=60, top-20 mỗi nhánh, top-10 vào rerank đều là điểm khởi đầu theo quy ước, chưa đo trên corpus GSM.

## Bài học

- RRF cần thứ hạng, không cần điểm cùng thang: đây là lý do chọn RRF thay vì cộng trực tiếp cosine với điểm BM25 (nối tiếp bài học Bước 0 về không đặt ngưỡng lên điểm RRF).
- Giới hạn token là ràng buộc cứng thứ hai sau embedding: reranker 512 token (ViRanker, và ví dụ dùng của bge-reranker-v2-m3) mang cùng rủi ro cắt im lặng đã thấy ở Bước 3; đây là lý do chính chọn AITeamVN (2304 token) thay vì mặc định theo độ nổi tiếng của bge-reranker-v2-m3.
- Benchmark tự công bố của các bản tinh chỉnh chỉ so được với baseline trong cùng bài đo của chính họ, không so chéo được giữa hai bài đo khác tập dữ liệu.
- Cross-encoder và bi-encoder (embedding) cần xử lý runtime khác nhau (điểm thô cần sigmoid, chạy theo cặp thay vì theo lô độc lập): giữ nguyên nguyên tắc Bước 3 — giấu chi tiết đó sau một interface, không để lộ ra retrieval logic.

## Tham khảo

- RRF gốc (Cormack, Clarke, Büttcher 2009): https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
- BAAI/bge-reranker-v2-m3: https://huggingface.co/BAAI/bge-reranker-v2-m3
- AITeamVN/Vietnamese_Reranker: https://huggingface.co/AITeamVN/Vietnamese_Reranker
- Qwen3-Reranker-0.6B: https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- ViRanker (arXiv 2509.09131): https://huggingface.co/namdp-ptit/ViRanker
- jina-reranker-v2-base-multilingual: https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual
- mxbai-rerank-v2: https://www.mixedbread.com/blog/mxbai-rerank-v2
- Cohere Rerank overview: https://docs.cohere.com/docs/rerank-overview
- Voyage rerank-2.5: https://blog.voyageai.com/2025/08/11/rerank-2-5/
- sentence-transformers CrossEncoder: https://sbert.net/docs/cross_encoder/usage/usage.html
