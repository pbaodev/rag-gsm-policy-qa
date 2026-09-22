# Bước 9: Eval

Bước cuối, phụ thuộc `retrieve` (Bước 5–6) và `generate` (Bước 7). Đúng như Bước 0 đã ghi ("Bộ câu hỏi vàng, chạy lại sau mỗi module"), mục đích không chỉ là "chấm điểm cuối" — mà là công cụ để chốt mọi tham số mà các Bước 3–7 đã cố tình để ngỏ chờ đo.

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Cấu trúc bộ câu hỏi vàng | jsonl, mỗi dòng: `{id, cau_hoi, chu_de, do_kho, nhanh_ky_vong, gold_chunk_ids, gold_answer, ghi_chu}` | Tách rõ 3 việc đo được — đúng chunk (retrieval), đúng nhánh (logic pipeline), đúng nội dung (generation); đúng khuyến nghị chuẩn "câu hỏi + câu trả lời đúng + tài liệu chứa câu trả lời" để phân biệt lỗi truy hồi với lỗi sinh câu trả lời |
| Kích thước | **50–100 câu** | (bạn chọn) Đủ lớn để chạy bảng bake-off (embedding, rerank, K, ngưỡng…) mà không nhiễu vì mẫu quá nhỏ; dùng lại được cho mọi bake-off sau này |
| Phân bổ theo chủ đề | Theo đúng bảng độ phủ đã kiểm kê ở Bước 1 (đặt xe, hủy chuyến, giá/thanh toán, hoàn tiền, khiếu nại, đồ thất lạc, privacy) + câu thuộc chủ đề "Không" (an toàn thông tin, SLA, RBAC) + câu đánh lừa cố ý (nghe hợp lý nhưng không có trong corpus) | Nhánh "không biết" phải được đo trực tiếp bằng câu hỏi thật, không chỉ nằm im trong sơ đồ (bài học đã ghi ở Bước 6) |
| Phân bổ theo độ khó truy hồi | Khớp tiêu đề trực tiếp / diễn đạt lại - từ đồng nghĩa / không dấu - dấu một phần / thuộc chủ đề "chưa có" | Bài thử BM25 ở Bước 4 chỉ có 8 câu sát tiêu đề, tự ghi "chưa kết luận được về tách từ" — bộ lần này phải sửa đúng thiếu sót đó |
| Viết gold answer | **LLM draft rồi tự kiểm lại**, đối chiếu nguồn gốc đã kiểm kê ở Bước 1 trước khi chốt | (bạn chọn) Nhanh hơn viết tay 50–100 câu; vẫn giữ bước tự kiểm để không lặp lại lỗi "tin thẳng công cụ tóm tắt" đã cảnh báo ở Bước 1 |
| Đo retrieval | Recall@k và MRR trên `gold_chunk_ids`; đo tách riêng ở 4 tầng: dense-only, BM25-only, sau RRF, sau rerank | Nhất quán với cách đã đo BM25 ở Bước 4; tách tầng để biết rerank có thực sự cải thiện so với RRF không, không chỉ nhìn đầu ra cuối |
| Đo quyết định nhánh | Bảng đối chiếu `nhanh_ky_vong` với nhánh thực chạy (hybrid / fallback / không biết); tính riêng tỉ lệ fallback nhầm (hybrid đã đúng nhưng vẫn rớt threshold) và bỏ sót fallback (đáng lẽ phải fallback nhưng không) | Ngưỡng rerank (Bước 5) và tiêu chí "đủ bằng chứng" (Bước 6) là tham số phải hiệu chỉnh bằng số đo, không đoán |
| Đo answer | LLM-judge bằng **Claude, temperature 0**, rubric 4 tiêu chí tách rời: đúng nội dung so với `gold_answer`; có căn cứ vào đúng chunk đã trích dẫn không (groundedness); `[n]` có trỏ đúng chunk liên quan không; nhánh "không biết" có kích hoạt đúng lúc không (cả hai chiều: từ chối khi có đủ info, và trả lời liều khi không đủ info) | Model sinh câu trả lời (`qwen3:4b`) yếu hơn model chấm — đúng khuyến nghị "giám khảo phải mạnh hơn thí sinh"; 4 tiêu chí tách rời để không lẫn "trả lời hay" với "trả lời đúng có căn cứ" |
| Hiệu chỉnh judge | Tự tay chấm 20–30 câu trước, so khớp với judge; chỉ tin judge khi đồng thuận ≥ 75–80% | Không tin LLM-judge mù quáng — cùng nguyên tắc "không tin công cụ tóm tắt" đã lặp lại xuyên suốt các bước trước, áp dụng cho cả công cụ chấm điểm |
| Baseline so sánh | "Nhét hết corpus liên quan vào prompt" (đã hẹn từ Bước 3 và Bước 6), chạy qua cùng bộ câu hỏi vàng và cùng judge | Biết RAG có thật sự hơn brute-force không, không chỉ giả định vì corpus chỉ ~40 nghìn token |
| Thư viện | **Tự viết**, không dùng RAGAS (Apache-2.0, dùng độc lập được, không bắt buộc LangChain) | RAGAS không có sẵn khái niệm nhánh "không biết" hay trích dẫn theo vị trí `[n]` của ta; vẫn phải viết rubric riêng nên lợi ích thư viện giảm nhiều, lại thêm phụ thuộc ngoài "tự viết lõi" đã chốt ở Bước 0.3 |
| Lưu kết quả | `eval/golden_questions.jsonl` (bộ câu hỏi) + `eval/runs/<config_id>.jsonl` (kết quả mỗi lần chạy, gắn config: model embedding, K, model rerank…) | So sánh được giữa các lần bake-off mà không ghi đè nhau, giống cách `data/chunks/<doc_id>.jsonl` đã tách theo tài liệu ở Bước 4 |

## Ma trận bake-off (tổng hợp mọi tham số "chờ eval" từ Bước 1–8)

| Tham số | Ứng viên cần so | Nguồn |
|---|---|---|
| Model embedding | bge-m3 (mặc định) so với Qwen3-Embedding-0.6B, gte-multilingual-base, multilingual-e5-large-instruct, AITeamVN/Vietnamese_Embedding, + 1 mốc API | Bước 3 |
| BM25: k1/b, stopwords, trọng số trường tiêu đề | Mặc định bm25s so với tinh chỉnh | Bước 4 |
| RRF: độ sâu top-N mỗi nhánh, có/không trọng số | k=60 / top-20 (mặc định) so với khác | Bước 5 |
| Model rerank | AITeamVN/Vietnamese_Reranker (mặc định) so với bge-reranker-v2-m3 gốc — kiểm xem bản tinh chỉnh có thực sự tốt hơn trên GSM hay chỉ tốt trên Legal Zalo | Bước 5 |
| Model chạy PageIndex fallback | `qwen3:4b` local (mặc định) so với Claude | Bước 6 |
| Độ dài trích đoạn outline (N ký tự) | Chưa chốt số | Bước 6 |
| Cỡ ngữ cảnh cuối | K=3 (mặc định) so với K=1 | Bước 7 |
| Context reorder | Có (mặc định) so với không, để xác nhận hiệu ứng có đáng kể ở K=3 hay không | Bước 7 |

Nguyên tắc chạy: đổi **một** tham số mỗi lần, giữ nguyên các tham số khác — không đổi hàng loạt cùng lúc, vì sẽ không biết tham số nào thực sự gây ra khác biệt.

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| RAGAS (hoặc TruLens, tương tự) | Không có sẵn khái niệm nhánh "không biết" hay trích dẫn theo vị trí `[n]`; vẫn phải viết rubric riêng nên lợi ích thư viện giảm nhiều | Nếu sau này mở rộng sang RAG tổng quát hơn, hoặc cần so sánh chéo với benchmark ngoài dùng RAGAS |
| nDCG cho retrieval | Cần chấm độ liên quan nhiều mức (0–3) cho mỗi chunk, tốn công gán nhãn hơn hẳn so với chỉ đánh dấu đúng/sai 1 gold chunk; Recall@k + MRR đã đủ ở quy mô này (đã dùng ở Bước 4) | Nếu một câu hỏi có nhiều chunk cùng liên quan ở các mức độ khác nhau cần phân biệt |
| Bộ câu hỏi vàng chỉ lấy nguyên câu hỏi FAQ có sẵn | Không đo được khả năng diễn đạt lại/từ đồng nghĩa — đúng lỗ hổng đã tự ghi ở Bước 4 | — |
| Chấm answer hoàn toàn bằng tay, không LLM-judge | Không scale khi cần chạy lại eval sau mỗi lần đổi tham số (8 hàng trong bảng bake-off ở trên) | Nếu bộ câu hỏi vàng đủ nhỏ (dưới ~20 câu) và không cần chạy lại nhiều lần |
| 30–50 câu | (bạn chọn) Nhanh hơn nhưng mẫu dễ quá nhỏ khi chia theo chủ đề × độ khó, kết quả bake-off dễ nhiễu | Nếu 50–100 câu vẫn tốn quá nhiều công so với thời gian có |
| Tự tay viết hoàn toàn gold answer | (bạn chọn) Chắc chắn không lệch ngay từ đầu nhưng tốn công đáng kể với 50–100 câu | Nếu LLM draft sai lệch nhiều khi tự kiểm, phải quay lại viết tay |

## Rủi ro và kiểm chứng

- LLM-judge (Claude) có thể thiên vị câu trả lời "nghe hợp lý" dù sai nội dung, hoặc chấm quá khắt khe với câu đúng nhưng diễn đạt khác `gold_answer` — đây chính là lý do bắt buộc hiệu chỉnh bằng tay (20–30 câu) trước khi tin kết quả judge trên toàn bộ 50–100 câu.
- Gold answer do LLM draft rồi một người tự kiểm: rủi ro người kiểm bỏ sót lỗi tinh vi mà LLM draft đưa vào (khác với việc tự viết từ đầu, nơi người viết buộc phải đọc kỹ nguồn) — cần đối chiếu trực tiếp với bảng kiểm kê nguồn ở Bước 1, không chỉ đọc lướt câu LLM draft.
- Bộ câu hỏi vàng do một người soạn (không phải khách hàng thật) có thể thiên về cách diễn đạt quen thuộc của người soạn — chấp nhận được cho MVP, cần ghi rõ giới hạn này khi báo cáo kết quả.
- Baseline "nhét hết corpus" phải đi qua đúng nhánh generation/citation như RAG thật (cùng ép trích dẫn `[n]`, cùng judge) để so sánh công bằng — nếu prompt baseline khác quá nhiều so với RAG thì so sánh mất ý nghĩa.
- Bảng bake-off có 8 tham số; nếu chạy tuần tự từng tham số một (đúng nguyên tắc kiểm soát biến số), tổng số lần chạy qua 50–100 câu có thể tốn thời gian đáng kể trên máy 16 GB — cần ước lượng thời gian một lượt chạy đầy đủ trước khi lên kế hoạch bake-off cả 8 tham số.

## Bài học

- "Giám khảo phải mạnh hơn thí sinh" là nguyên tắc đơn giản nhưng dễ bỏ qua: nếu dùng cùng `qwen3:4b` để chấm chính câu trả lời nó vừa sinh ra, sai lầm hệ thống của nó sẽ lặp lại y hệt trong cả câu trả lời lẫn lời chấm.
- "Chunk đúng", "nhánh đúng", "nội dung đúng" là ba loại lỗi khác nhau (retrieval, quyết định pipeline, generation) và phải đo tách biệt — gộp chung vào một điểm số duy nhất sẽ không biết sửa ở đâu khi eval kém.
- Nguyên tắc "không tin công cụ tóm tắt, phải tự kiểm" (Bước 1) áp dụng nguyên vẹn cho LLM-judge lẫn LLM-draft-gold-answer: một công cụ chấm điểm hay soạn câu trả lời mẫu vẫn là một LLM có thể sai, phải hiệu chỉnh/đối chiếu bằng tay trước khi tin.
- Bảng bake-off tổng hợp cho thấy phần lớn quyết định "mặc định" của Bước 3–7 đều ghi rõ "chờ eval" — kiến trúc đã xong nhưng gần như mọi con số cụ thể vẫn là giả thuyết. Đây chính là nguyên tắc đã chốt từ Bước 0: "mọi tham số phải có eval đo, không đoán" — Bước 9 không phải bước phụ để kiểm tra cuối cùng, mà là nơi phần lớn các bước trước thực sự được hoàn tất.

## Tham khảo

- RAGAS (tham khảo phương pháp, không dùng làm thư viện): https://github.com/explodinggradients/ragas
- Langfuse — RAG faithfulness evaluation với LLM-as-judge: https://langfuse.com/resources/engineering/rag-faithfulness-evaluation
- Braintrust — RAG evaluation, cấu trúc golden dataset: https://www.braintrust.dev/articles/what-is-rag-evaluation
