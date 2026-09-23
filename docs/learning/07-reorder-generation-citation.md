# Bước 7: Context reorder + Generation + Citation

Corpus: chính sách GSM tiếng Việt. Bước này nhận danh sách chunk đã qua ngưỡng (từ Bước 5 hybrid+rerank, hoặc Bước 6 PageIndex fallback), xếp lại thứ tự, ghép prompt, sinh câu trả lời và trích dẫn.

**Code thật 2026-09-22:** đã nối toàn bộ đường đi thật (`rag_gsm/retrieve/pipeline.py` gộp Bước 5/6, `rag_gsm/generate/{prompt,citation,answer,llm_adapter}.py` cho Bước 7) và chạy trên corpus 337 chunk thật với Ollama `qwen3:4b` thật. Cả 3 nhánh đều chạy đúng: "hủy chuyến xe có bị trừ tiền không" → nhánh hybrid, trả lời có `[1]` đúng chunk `faq#3.6`; một câu hỏi ngoài phạm vi (công thức nấu ăn) → fallback không đủ bằng chứng → nhánh "không biết" với hotline/email thật, không gọi LLM sinh câu trả lời. Phát hiện quan trọng nhất: `qwen3:4b` là reasoning model, tốn 65–103 giây thật cho một lượt trả lời/fallback vì "nghĩ" ẩn hàng trăm–nghìn token trước khi ra chữ — xem `CLAUDE.md` mục "Generate gotchas" để biết chi tiết và vì sao `"think": false` không dùng được.

**Bug thật 2026-09-23 (sau khi đổi sang `qwen2.5:3b`):** chủ dự án tự bấm thử UI, hỏi đúng câu "Hủy chuyến xe có bị trừ tiền không?" và nhận được câu trả lời **chỉ đúng chữ `[1]`, không có câu văn nào**. Tái hiện được ngay (`done_reason: "stop"`, `eval_count: 4` — model thật sự dừng sau 4 token, không phải bug timeout/cắt bớt trong code). Nguyên nhân, tìm bằng cách thử bớt từng phần system prompt: prompt cũ nêu quy tắc chèn `[n]` kèm một ví dụ để trần trong ngoặc vuông ("... ví dụ [1] hoặc [2]") mà không hề nói rõ "hãy VIẾT một câu trả lời" — `qwen2.5:3b` (model yếu hơn, bám khuôn mẫu hơn) đọc ví dụ đó như thể đó chính là định dạng output cần trả về, bỏ qua luôn phần diễn giải. Sửa: viết lại `SYSTEM_PROMPT` thành một nhiệm vụ viết rõ ràng ("viết một đoạn trả lời đầy đủ, tự nhiên...") kèm cấm rõ ràng ("không bao giờ được trả lời chỉ bằng một trích dẫn trơ trọi"). Kiểm lại bằng đúng câu hỏi lỗi và 2 câu đang chạy tốt khác — cả 3 đều ra câu trả lời đầy đủ, không còn hiện tượng cũ. Thêm `tests/test_prompt.py::test_system_prompt_forbids_bare_citation_only_answer` để giữ lại cụm câu cấm này trong prompt.

## Sơ đồ (đã chốt ở Bước 0)

```
top-1 ≥ ngưỡng (Bước 5) ─┐
đủ bằng chứng (Bước 6)  ─┴→ lấy top-K chunk → Context reorder → LLM → Answer + Citation
```

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Hội thoại | **Single-turn** — mỗi câu hỏi xử lý độc lập | (bạn chọn) Khớp cách hỏi FAQ thật (câu hỏi khách thường tự đủ nghĩa — Bước 1); đơn giản hơn, không cần lệnh gọi LLM viết lại câu hỏi theo lịch sử |
| Cỡ ngữ cảnh cuối | **Top-3 cố định** (K=3) sau rerank | (bạn chọn) Pool rerank ở Bước 5 đã nhỏ (top-10); K cố định đơn giản, dễ tune bằng eval hơn ngưỡng tương đối |
| Context reorder | **Sandwich**: hạng 1 và 2 ở hai đầu prompt, hạng kém nhất ở giữa | Giảm hiệu ứng "lost in the middle" (Liu et al. 2023, arXiv:2307.03172): LLM chú ý nhiều nhất vào đầu và cuối prompt, ít nhất ở giữa |
| Trích dẫn | Số thứ tự **`[n]`** khớp thứ tự khối ngữ cảnh trong prompt, không phải `chunk_id` | (bạn chọn) Model 3–4B chỉ cần ghi đúng một số nguyên nhỏ, ít rủi ro bịa hơn tự ghi `chunk_id`; hệ thống giữ bảng ánh xạ `n → chunk_id` riêng |
| Kiểm chứng trích dẫn | Validate `n` ∈ 1..K sau khi sinh xong; luôn kèm danh sách nguồn đầy đủ ở cuối bất kể `[n]` có xuất hiện đúng hay không | Model có thể bỏ sót hoặc ghi sai số; danh sách nguồn là lưới an toàn để khách luôn tra được văn bản gốc |
| Temperature | Thấp (0,1–0,2) | Hỏi đáp chính sách cần nhất quán, giảm bịa đặt hơn là sáng tạo |
| Nhánh "không biết" | Câu trả lời cố định, kèm hotline 1555 và email hỗ trợ | Tái dùng kênh CSKH thật đã kiểm kê ở Bước 1 (FAQ 6.4); không để trống khi hệ thống không đủ bằng chứng |
| Ngôn ngữ | Luôn tiếng Việt | Khớp corpus và người dùng mục tiêu (Bước 0) |

## Context reorder: thuật toán

Input: chunk đã xếp hạng tốt → kém (điểm rerank Bước 5, hoặc thứ tự `node_list` Bước 6). Xếp xen kẽ: hạng lẻ (1, 3, 5, …) đặt từ đầu prompt vào giữa; hạng chẵn (2, 4, …) đặt từ cuối prompt lùi vào giữa. Kết quả: hạng 1 ở đầu, hạng 2 ở cuối, chunk kém nhất rơi vào giữa.

Ví dụ K=3, hạng giảm dần `[A(1), B(2), C(3)]` → thứ tự đưa vào prompt: `A, C, B` (A đầu, B cuối, C — kém nhất — ở giữa).

Tự viết lại thuật toán này (không dùng `LongContextReorder` của LangChain — Bước 0.3 đã chốt không dùng LangChain); bản chất chỉ là một hàm sắp xếp lại danh sách, không cần thư viện.

## Trích dẫn: cơ chế

1. Mỗi khối ngữ cảnh trong prompt đánh số theo thứ tự **sau khi đã reorder** (không phải thứ tự rerank gốc); hệ thống giữ bảng ánh xạ riêng `n → {chunk_id, nguồn (URL), heading_path, trang nếu có}`.
2. LLM được yêu cầu chèn `[n]` ngay sau các khẳng định lấy từ nguồn.
3. Sau khi sinh xong: parse mọi `[n]` xuất hiện, validate `n` nằm trong 1..K; bỏ qua số không hợp lệ (không chặn câu trả lời).
4. Hiển thị danh sách nguồn đầy đủ (từ bảng ánh xạ) ở cuối câu trả lời và trong trace panel (Bước 8), bất kể `[n]` có được model chèn đúng hay không.

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| Multi-turn với viết lại câu hỏi ngay từ đầu | (bạn chọn) Thêm 1 lệnh gọi LLM mỗi câu hỏi và thêm điểm có thể sai (viết lại sai → truy hồi sai); câu hỏi chính sách thường tự đủ nghĩa | Nếu người dùng thật hỏi nối tiếp nhiều và eval cho thấy single-turn bỏ lỡ ngữ cảnh |
| Ngưỡng tương đối cho cỡ ngữ cảnh (≥X% điểm top-1) | (bạn chọn) Thêm một tham số (X%) phải tune trước khi có baseline K cố định để so | Nếu eval cho thấy K cố định cắt mất chunk liên quan khi điểm rerank sát nhau, hoặc lẫn chunk không liên quan khi điểm cách xa |
| LLM tự ghi `chunk_id` trực tiếp | (bạn chọn) Rủi ro cao nhất với model 3–4B: dễ ghi sai định dạng hoặc bịa `chunk_id` không tồn tại | Nếu đổi sang Claude cho bước generation và đo thấy model tuân thủ định dạng tốt |
| Chỉ liệt kê nguồn cuối câu trả lời, không trích dẫn trong dòng | (bạn chọn) An toàn nhất nhưng không chỉ rõ câu nào lấy từ nguồn nào — mất phần lớn giá trị học về grounding | Nếu `[n]` inline gây nhiễu hoặc model không tuân thủ được sau nhiều lần thử |
| Không reorder, giữ nguyên thứ tự rerank | Bỏ qua hiệu ứng lost-in-the-middle đã có bằng chứng; chi phí cài gần như 0 vì chỉ là một hàm sắp xếp | Không có lý do đổi lại, trừ khi eval cho thấy reorder không tạo khác biệt ở K=3 (khả năng cao vì K nhỏ) |
| Dùng `LongContextReorder` của LangChain | Bước 0.3 đã chốt không dùng LangChain; thuật toán đơn giản, tự viết không tốn công đáng kể | — |

## Rủi ro và kiểm chứng

- K=3 chưa đo: nhiều câu hỏi FAQ chỉ cần đúng 1 chunk tự đủ nghĩa, K=3 có thể thêm 2 chunk không liên quan làm nhiễu câu trả lời — so sánh K=1 và K=3 trên eval (Bước 9).
- Hiệu ứng "lost in the middle" đo trên tiếng Anh và ngữ cảnh dài hơn nhiều so với 3 chunk ngắn; với K=3, "giữa" chỉ có đúng 1 chunk — chưa chắc hiệu ứng còn đáng kể ở quy mô này. Cần so sánh có/không reorder trên eval trước khi coi đây là cải thiện thật, không chỉ áp dụng vì lý thuyết.
- Validate `[n]` chỉ bắt được số ngoài khoảng hoặc thiếu, không bắt được trường hợp trích đúng vị trí nhưng diễn giải sai nội dung của chunk đó — eval cần kiểm cả nội dung câu trả lời so với chunk được trích, không chỉ tính hợp lệ của số trích dẫn.
- ~~Chưa đo `qwen3:4b` có chèn `[n]` đều đặn hay bỏ sót phần lớn~~ — **sửa 2026-09-22: đã thử thật, không đều.** Có lần model trả về nguyên chữ `[n]` thay vì số thật thay vào. Hệ thống không vá bằng cách sửa chữ model trả về — `citation.py` chỉ khớp số, bỏ qua `[n]` không hợp lệ một cách an toàn, và danh sách nguồn cuối câu trả lời luôn đầy đủ bất kể model có trích đúng hay không — đúng như quyết định "luôn kèm danh sách nguồn đầy đủ" ở trên, nay có bằng chứng thật để giữ quyết định đó thay vì chỉ là phòng xa.
- Nhánh "không biết" cố định lấy hotline (1555) và email (`support.vn@greensm.com`) từ đúng chunk thật (`faq#1.1-b`, `dieu-khoan-su-dung#11.p1-11.p3`), nhưng câu chữ bọc quanh hai thông tin đó chưa được người biết giọng CSKH thật của GSM duyệt lại — vẫn nên đọc lại vài câu trả lời FAQ (Bước 1) để khớp văn phong trước khi coi câu chữ này là bản cuối.
- **Mới phát hiện khi chạy thật (2026-09-22):** `qwen3:4b` là reasoning model, "nghĩ" ẩn trước khi trả lời — 65 giây/~900 token nghĩ cho một câu trả lời 1-chunk, và tới ~103 giây cho một lượt PageIndex fallback trên outline 337 chunk. `"think": false` (tham số Ollama để tắt nghĩ) không hoạt động đúng trên bản Ollama đang dùng: nội dung nghĩ bị dồn thẳng vào `message.content` kèm thẻ `</think>` thô, còn chậm hơn (101s) và sẽ rò rỉ vào câu trả lời khách nếu tin thẳng. Chưa giải quyết — xem `CLAUDE.md` "Known loose ends" về việc chọn model khác hoặc chấp nhận độ trễ cho `ui` (Bước 8).

## Bài học

- "Lost in the middle" là hiện tượng về **vị trí trong prompt**, không phải về nội dung — thuật toán sửa nó (sandwich) không cần LLM, chỉ cần sắp lại thứ tự đưa vào, đúng tinh thần "tự viết lõi" ở Bước 0.3.
- Trích dẫn theo số thứ tự trong prompt (thay vì `chunk_id` thật) tách "thứ LLM phải nhớ đúng" khỏi "thứ hệ thống phải map đúng": model chỉ cần đếm 1, 2, 3; hệ thống lo phần còn lại — cùng nguyên tắc giấu chi tiết sau interface đã lặp lại ở Bước 3 (`embed_query`/`embed_documents`) và Bước 5 (`CrossEncoder`).
- Ép trích dẫn không chỉ để hiển thị nguồn cho khách — nó còn là một ràng buộc mềm giúp giảm bịa đặt (model phải "chỉ tay" vào một khối cụ thể); vẫn cần danh sách nguồn làm lưới an toàn thứ hai vì đây không phải ràng buộc cứng.

## Tham khảo

- Lost in the Middle: How Language Models Use Long Contexts (Liu et al., 2023): https://arxiv.org/abs/2307.03172
- LangChain — Long Context Reorder (mô tả thuật toán, không dùng thư viện): https://python.langchain.com/v0.2/docs/how_to/long_context_reorder/
