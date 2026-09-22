# Bước 8: Streamlit UI (chat + trace panel)

Module cuối, phụ thuộc `generate` (Bước 7). Hai việc: giao diện chat như khách hàng thật sẽ dùng, và một trace panel để quan sát nội bộ từng lượt truy vấn — công cụ chính để soi pipeline bằng mắt song song với eval tự động (Bước 9). Chạy local (Bước 0), không host công khai.

**Đã xác nhận lại framework** (thảo luận trước khi viết doc này): giữ **Streamlit**, so với Gradio (hợp demo model đơn giản hơn là dashboard nhiều bảng) và Chainlit (có `@cl.step` dựng cây bước sẵn, nhưng chỉ tự động khi dùng LangChain/LlamaIndex — pipeline này tự viết lõi nên vẫn phải tự gắn bước thủ công, mất lợi thế đó). Streamlit mạnh hơn ở đúng thứ trace panel cần: bảng, biểu đồ, sidebar, expander.

## Sơ đồ

```
Generate (Bước 7): Answer + Citation
        ↓
Streamlit: chat message + expander trace (bên dưới câu trả lời)
```

## Chốt

| Việc | Chọn | Vì sao |
|---|---|---|
| Vị trí trace panel | **Expander dưới mỗi câu trả lời** trong chat thread | (bạn chọn) Cuộn lại xem được trace của mọi câu đã hỏi trong phiên — hợp mục tiêu học, so sánh nhiều câu hỏi |
| Hiển thị câu trả lời | **Chờ tính xong rồi hiện một lần** (không streaming từng token) | (bạn chọn) Đơn giản nhất để viết; khớp tinh thần "bắt đầu đơn giản, đo rồi mới thêm" đã lặp lại từ Bước 4 (BM25 một chỉ mục) và Bước 7 (single-turn); thêm streaming sau nếu độ trễ thật sự khó chịu |
| Cache tài nguyên nặng | `st.cache_resource` cho embedder, reranker, kết nối LanceDB, chỉ mục bm25s, client LLM | Streamlit chạy lại toàn bộ script mỗi lần tương tác; không cache thì load lại model mỗi câu hỏi, không chấp nhận được |
| Lịch sử hội thoại | `st.session_state["messages"]`, mỗi message của assistant lưu kèm dict trace riêng | Cần dict trace riêng theo từng message để expander của đúng câu đó hiện đúng dữ liệu khi Streamlit rerun và vẽ lại toàn bộ lịch sử |
| Input | `st.chat_input`; **không** dùng lịch sử hội thoại để truy hồi | Đúng quyết định single-turn ở Bước 7 — lịch sử chỉ để hiển thị, không đưa vào truy vấn |
| Lỗi/timeout | `try/except` quanh mọi lệnh gọi model (embedder, reranker, LLM); hiện thông báo lỗi thân thiện, không crash cả app | Model local (Ollama) có thể chưa chạy hoặc timeout; một câu hỏi lỗi không nên làm mất lịch sử phiên |

## Nội dung trace panel

Mỗi expander chứa, theo đúng dữ liệu **đã lọc audience/`doi_tuong`** (không query lại không lọc chỉ để hiện):

| Phần | Nội dung |
|---|---|
| Nhánh đã chạy | Hybrid (Bước 5) / PageIndex fallback (Bước 6) / "Không biết" |
| Nếu hybrid | Bảng ứng viên trước rerank (hạng + điểm dense, hạng + điểm BM25, điểm RRF); bảng sau rerank (điểm đã sigmoid), đánh dấu có vượt ngưỡng không; top-3 được chọn; thứ tự sau reorder (sandwich, Bước 7) |
| Nếu fallback | Số node trong outline đã gửi; `node_list` LLM chọn kèm `trich_dan`; kết luận đủ/không đủ bằng chứng |
| Trích dẫn | Bảng ánh xạ `[n] → chunk_id, nguồn (URL), heading_path, trang (nếu có)` |
| Độ trễ | Thời gian từng bước (truy hồi, rerank, fallback nếu có, sinh câu trả lời) và tổng |
| Prompt thô | Một expander lồng bên trong, **đóng mặc định** ("Xem prompt đầy đủ gửi LLM") — không hiện ngay để tránh rối chat thread, nhưng vẫn có lối xem sâu khi cần debug |

## Không chọn

| Phương án | Vì sao không | Khi nào đổi |
|---|---|---|
| Sidebar cố định, chỉ hiện trace câu gần nhất | (bạn chọn) Mất trace của câu hỏi trước khi hỏi câu mới, không so sánh được nhiều câu hỏi trong một phiên | Nếu chat thread quá dài khiến expander lịch sử làm chậm trang |
| Streaming từng token | (bạn chọn) Trích dẫn `[n]` vẫn chỉ parse được sau khi có đủ văn bản (Bước 7), nên lợi ích chỉ là cảm nhận tốc độ, không đổi được logic; thêm phức tạp không cần thiết lúc đầu | Nếu đo latency thật của `qwen3:4b` local vượt vài giây rõ rệt và gây khó chịu |
| Gradio | Dựng nhanh kiểu "nhập → xuất" nhưng kém hợp bố cục nhiều bảng/biểu đồ của trace panel | Nếu sau này chỉ cần demo model đơn giản, bỏ hẳn trace panel |
| Chainlit | Lợi thế cây bước tự động chỉ có khi dùng LangChain/LlamaIndex; pipeline này tự viết lõi nên vẫn phải tự gắn bước thủ công như Streamlit, trong khi Chainlit yếu hơn ở hiển thị bảng số liệu | Nếu sau này đổi sang dùng LangChain/LlamaIndex thật (trái quyết định Bước 0.3) |
| Luôn hiện toàn bộ prompt thô ngay, không ẩn | Quá nhiều thông tin gây rối chat thread mỗi câu hỏi | — |
| Host công khai (Streamlit Community Cloud) | Dự án chạy local theo Bước 0; corpus công khai nhưng adapter LLM/model chạy máy cá nhân | Nếu muốn demo cho người khác xem từ xa |

## Rủi ro và kiểm chứng

- Streamlit rerun toàn bộ script mỗi lần tương tác: nếu cache sai cách (ví dụ dùng `st.cache_data` thay vì `st.cache_resource` cho object không serialize được như model/kết nối DB), sẽ lỗi hoặc load lại mỗi lần — cần kiểm khi cài.
- Trace panel phải dùng đúng kết quả đã lọc `doi_tuong`/`audience` từ Bước 4–6; nếu code hiển thị vô tình query lại không lọc "cho đẹp", sẽ mở lại lỗ hổng an toàn mà Bước 4 đã cố tình đóng bằng cấu trúc thư mục `index/public` / `index/internal`.
- Chưa đo latency thật của toàn chuỗi (dense + BM25 + RRF + rerank + generation) trên máy 16 GB với `qwen3:4b` — quyết định "chờ đủ rồi hiện" có thể phải đảo lại thành streaming nếu độ trễ vượt ngưỡng chấp nhận được.
- `session_state` lưu trace dict cho mỗi message có thể phình to nếu phiên chat dài — chấp nhận được cho dự án học/demo cá nhân, không cần tối ưu bộ nhớ ở MVP.

## Bài học

- Trace panel không phải "để cho đẹp" — nó phải phản chiếu đúng dữ liệu đã lọc an toàn, nếu không sẽ vô tình mở lại lỗ hổng mà một bước trước đó đã cố tình đóng bằng cấu trúc (bài học lặp lại từ Bước 4: "an toàn bằng cấu trúc, không chỉ bằng bộ lọc").
- Mô hình "rerun toàn bộ script" của Streamlit buộc phải tách rõ hai loại state khác nhau: tài nguyên nặng dùng chung giữa mọi phiên (`cache_resource`) và trạng thái hội thoại riêng từng phiên (`session_state`) — lẫn hai loại này sẽ vừa chậm vừa sai.
- "Chờ đủ rồi hiện" không mâu thuẫn gì với thiết kế trích dẫn ở Bước 7 (vẫn phải parse `[n]` sau khi có đủ văn bản dù có streaming hay không) — chọn đơn giản trước không tốn chi phí tương thích nào về sau, chỉ là hoãn một việc UI chưa chắc cần ngay.

## Tham khảo

- Streamlit chat elements: https://docs.streamlit.io/develop/api-reference/chat
- st.cache_resource: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
- Session State: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
