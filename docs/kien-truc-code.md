# Kiến trúc code (trước khi build)

Tài liệu này khác các file trong `docs/learning/`: không brainstorm lại quyết định (đã chốt ở Bước 0–9), chỉ định hình "cài đặt thế nào" — cấu trúc thư mục, interface dùng chung giữa các module, config. Mục tiêu: `ingest` không phải sửa lại khi `index`/`retrieve` cần một kiểu dữ liệu khác.

## Cấu trúc thư mục

```
rag_gsm/
  config.py            # đọc config/*.toml
  schemas.py           # Document, Chunk, RetrievalCandidate, RetrievalResult, TraceInfo, Answer, Citation
  ingest/
    web.py              # httpx + fetch __NEXT_DATA__ (hoac HTML tho khi trang khong co JSON)
    heading.py           # dung heading tu so thu tu (1. / 1.1. / 1.1.1.) - o day, khong phai chunk/,
                         # vi "dung heading" la viec cua ingest (Buoc 1); chunk chi quyet dinh RANH GIOI chunk
    extractors/         # 1 file/loai trang: general.py, privacy.py, faq.py, ewallet.py, insurance.py
    ocr.py               # Docling cho 56 ảnh Quy chế hoạt động
    normalize.py         # NFC, content_hash, regex ngay_hieu_luc, ghi front matter
  chunk/
    loader.py             # doc lai data/markdown/*.md (front matter + than) thanh Document
    rules.py              # quy tac gom/tach chunk theo nhom: faq, dieu_khoan, bang, quy_che; gan doi_tuong theo khoan
    run.py                # chay rules tren toan bo data/markdown/*.md, ghi data/chunks/<doc_id>.jsonl
  index/
    embedder.py           # Embedder (Protocol) + bge-m3 impl
    dense_store.py         # LanceDB
    bm25_store.py           # bm25s, âm tiết bỏ dấu
    build.py                # dựng lại index/public, index/internal từ data/chunks
  retrieve/
    hybrid.py                # RRF
    rerank.py                  # AutoModelForSequenceClassification wrapper (không phải CrossEncoder - xem "Bug thật" dưới)
    _tokenizer_repair_script.py  # sửa tokenizer.json thiếu cho AITeamVN/Vietnamese_Reranker, chạy qua `uv run --with`
    fallback.py                 # outline + LLM chọn node (PageIndex)
    reorder.py                   # sandwich
  generate/
    llm_adapter.py                # LLMAdapter (Protocol) + OllamaAdapter, ClaudeAdapter
    prompt.py                      # ghép prompt, parse [n], map citation
  ui/
    app.py                          # Streamlit
  eval/
    metrics.py                      # Recall@k, MRR
    judge.py                          # LLM-judge, rubric 4 tiêu chí
    run.py                            # chạy golden_questions.jsonl, ghi eval/runs/<config_id>.jsonl

config/
  default.toml
data/            # layout đã chốt ở Bước 1, 4
index/
eval/
  golden_questions.jsonl
  runs/
docs/
  kien-truc-code.md   # file này
  learning/
tests/
  test_heading.py, test_ingest.py, test_bm25.py, test_lancedb_filter.py, test_rrf.py, ...
pyproject.toml
```

`uv` + Python 3.12 (Bước 0); một package `rag_gsm`, không tách nhiều repo.

## Interface dùng chung

Các dataclass này là "hợp đồng" giữa module — đổi field ở đây nghĩa là đổi ở mọi module dùng nó, nên chốt trước khi code lan ra nhiều nơi. Tên field giữ đúng như đã chốt trong `docs/learning/` (không đặt lại tên).

```python
# schemas.py

@dataclass
class Document:              # đầu ra ingest, đầu vào chunk — front matter Bước 1
    doc_id: str
    source: str
    title: str
    doc_type: str             # faq | dieu_khoan | chinh_sach | quy_che | bao_hiem
    audience: str              # khach_hang | noi_bo
    nguon_tin_cay: str          # chinh_thuc | bao_chi | cong_dong | noi_bo
    fetched_at: str
    content_hash: str
    ngay_hieu_luc: str | None
    markdown_path: str

@dataclass
class Chunk:                  # đầu ra chunk, đầu vào index — metadata Bước 2
    chunk_id: str              # "general#3.2", "faq#3.6"
    doc_id: str
    parent_id: str | None
    doc_type: str
    heading_path: str
    breadcrumb: str             # "Văn bản › mục › khoản" — dùng cho embed, BM25, outline fallback
    text: str                    # nội dung chunk, KHÔNG kèm breadcrumb
    so_muc: str | None
    doi_tuong: str                # nguoi_dung | doi_tac | chung
    audience: str
    nguon_tin_cay: str
    ngay_hieu_luc: str | None
    trang_bat_dau: int | None
    trang_ket_thuc: int | None
    loai_chunk: str                 # faq | dieu_khoan | bang | generic
    source: str
    token_count: int

    def text_to_index(self) -> str:
        return f"{self.breadcrumb}\n{self.text}"   # breadcrumb đứng đầu (Bước 2)

class Embedder(Protocol):            # Bước 3 — giấu prefix/instruction riêng từng model
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...

@dataclass
class RetrievalCandidate:             # một chunk qua các tầng điểm — để trace panel (Bước 8)
    chunk_id: str
    dense_score: float | None = None
    dense_rank: int | None = None
    bm25_score: float | None = None
    bm25_rank: int | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None    # đã sigmoid, 0–1 (Bước 5)

@dataclass
class TraceInfo:                       # toàn bộ dữ liệu nội bộ 1 lượt truy vấn (Bước 8)
    branch: Literal["hybrid", "pageindex_fallback", "khong_biet"]
    candidates_before_rerank: list[RetrievalCandidate] = field(default_factory=list)
    candidates_after_rerank: list[RetrievalCandidate] = field(default_factory=list)
    threshold: float = 0.0
    fallback_outline_size: int | None = None
    fallback_node_list: list[dict] | None = None     # [{chunk_id, trich_dan}] — Bước 6
    citation_map: dict[int, str] = field(default_factory=dict)   # n -> chunk_id
    latency_ms: dict[str, float] = field(default_factory=dict)

@dataclass
class RetrievalResult:                 # đầu ra Bước 5/6, đầu vào Bước 7
    branch: str
    chunks: list[Chunk]                 # đã reorder (sandwich), tối đa K=3
    trace: TraceInfo

@dataclass
class Citation:
    n: int
    chunk_id: str
    source: str
    heading_path: str
    trang: int | None = None

@dataclass
class Answer:                           # đầu ra Bước 7, đầu vào UI + eval
    text: str                            # có [n] inline
    citations: list[Citation]
    branch: str

class LLMAdapter(Protocol):              # Bước 0 adapter mỏng — Ollama dev, Claude khi cần chất lượng
    def generate(self, system: str, user: str) -> str: ...
    def generate_json(self, system: str, user: str, schema_hint: str) -> dict: ...  # PageIndex node_list, LLM-judge

@dataclass
class GoldenQuestion:                     # Bước 9
    id: str
    cau_hoi: str
    chu_de: str
    do_kho: str
    nhanh_ky_vong: str                     # hybrid | pageindex_fallback | khong_biet
    gold_chunk_ids: list[str]
    gold_answer: str
    ghi_chu: str = ""

@dataclass
class JudgeVerdict:                        # Bước 9 — rubric 4 tiêu chí tách rời
    question_id: str
    dung_noi_dung: bool
    groundedness: float                     # 0–1
    citation_dung: bool
    khong_biet_dung_luc: bool
    ghi_chu: str = ""
```

## Config (`config/default.toml`)

Không hard-code model/tham số trong code — mọi thứ "chờ eval" ở Bước 9 nằm ở đây, để bake-off chỉ cần đổi file config, không sửa code.

```toml
[embedding]
model = "BAAI/bge-m3"

[bm25]
k1 = 1.5
b = 0.75

[rrf]
k = 60
top_n_per_branch = 20

[rerank]
model = "AITeamVN/Vietnamese_Reranker"
top_k_into_rerank = 10

[context]
final_k = 3
reorder = true

[fallback]
model = "ollama:qwen3:4b"        # hoặc "claude:<model-id>"
excerpt_chars = 200                # N ký tự đầu chunk trong outline — CHƯA CHỐT, xem Bước 6

[generation]
model = "ollama:qwen3:4b"
temperature = 0.15

[thresholds]
rerank_pass = 0.5                   # PLACEHOLDER — phải hiệu chỉnh ở Bước 9, không dùng số này để kết luận gì
```

Đọc bằng `tomllib` (built-in từ Python 3.11), không cần thêm thư viện.

## Task list: `ingest` (đã code, 2026-09-22)

Sửa lớn so với bản kế hoạch ban đầu: hầu hết trang là JSON sạch trong `__NEXT_DATA__`, không phải DOM cần cạo — xem `docs/learning/01-ingestion.md` (mục sửa 2026-09-22) để biết vì sao. `doi_tuong` **không** phải việc của ingest — đó là nhãn theo khoản, gán lúc **chunk** (Bước 2), sau khi đã có heading; ingest chỉ tạo Markdown có heading đúng để chunk dựa vào.

1. `web.py` — `httpx` fetch + regex lấy `<script id="__NEXT_DATA__">…</script>`, `json.loads`. ✅ Xong.
2. `heading.py` — tách dòng theo `\r\n`, nhận `1.`→H1, `1.1.`→H2, `1.1.1.`→H3; **lột thẻ HTML inline trước khi so khớp** (`<strong>`, `<i>`, `<a href>`→Markdown link) — một số Phụ lục đánh dấu tiêu đề bằng `<strong>` thay vì dòng số trần, phát hiện khi chạy thật, không đoán trước được. ✅ Xong, có test.
3. `normalize.py` — NFC, `content_hash` (sha256), regex `ngay_hieu_luc`, ghép front matter YAML. ✅ Xong, có test.
4. `extractors/general.py` — `generalTerms.generalItems[]` (16 phần tử) → 15 `Document` (bỏ `[12]`, trùng `privacy.py`). ✅ Xong.
5. `extractors/privacy.py` — `privacyNotice.privacyItems[]` (14 mục đã đánh số + đặt tên sẵn). ✅ Xong.
6. `extractors/insurance.py` — `insuranceData.{columns, rows}`; `columns` là chuỗi nối `"|"`, `rows` là dict `{value1, value2, …}` theo vị trí, **không phải list cột** như đoán ban đầu. ✅ Xong.
7. `extractors/faq.py` — `contentFaq.setUpFaq`, lọc nhóm "Dành cho người dùng" (49 câu, 6 danh mục); lột HTML khỏi câu hỏi/câu trả lời (link `<a href>` trỏ sang trang Bảo hiểm). ✅ Xong.
8. `run.py` — chạy 4 extractor trên, ghi `data/markdown/<doc_id>.md`. ✅ Xong.
9. **Chưa làm:** `ocr.py` (56 ảnh Quy chế hoạt động → Docling), tìm lại "Điều khoản ví E-Green" (URL cũ không còn), và ghi `data/raw/{web,images}/` (hiện `web.py` chỉ fetch trong bộ nhớ, không lưu HTML gốc — lệch với quyết định "giữ file gốc" ở Bước 1, xem `CLAUDE.md` "Known loose ends").

### Test đã viết

`tests/test_heading.py`, `tests/test_normalize.py`, `tests/test_insurance_extractor.py` — dùng đoạn mẫu chép tay từ dữ liệu thật (không toàn văn), phong theo đúng các bug đã gặp (tiêu đề bọc `<strong>`, `columns` là chuỗi không phải list) để không tái phát khi refactor. Chưa có test cho `extractors/general.py` (cần mạng); nếu muốn test không cần mạng, thêm fixture JSON rút gọn vào `tests/fixtures/`.

## Task list: `chunk` (đã code, 2026-09-22)

Đếm token bằng chính tokenizer bge-m3 (`transformers.AutoTokenizer`, không cần torch, chỉ tokenize) — không dùng ước lượng từ/token, vì `02-chunking.md` đã ghi rõ số đo cũ (median/p90) chỉ đo trên `generalItems[0]` và cần đo lại khi code chunk thật.

1. `loader.py` — đọc lại front matter (`key: value`, chuỗi dạng Python repr) + thân Markdown từ file `.md` ingest đã ghi. ✅ Xong, có test.
2. `rules.py` — dựng cây từ heading `#`/`##`/`###` (độ sâu = số `#`, không giả định H1 luôn có mặt — `phu-luc-07` chỉ có H2 vì tiêu đề cấp 1 viết "ĐIỀU N." thay vì "N.", ngoài khuôn mà `heading.py` nhận, chunk vẫn chạy đúng vì không đoán lại cấp cha). Với mỗi nhóm cấp 1: thử cả nhóm làm 1 chunk nếu vừa ngân sách và không trộn `doi_tuong`; nếu không, gom khoản cấp 2 liên tiếp cùng nhãn (không bao giờ trộn khác nhãn dù vẫn vừa ngân sách — invariant, không phải tối ưu kích thước). FAQ: 1 câu hỏi = 1 chunk cố định, chỉ tách khi vượt ngân sách. Bảng bảo hiểm: cả bảng 1 chunk + viết lại hàng thành câu. ✅ Xong, có test.
3. `run.py` — chạy trên 18 tài liệu, ghi `data/chunks/<doc_id>.jsonl`. ✅ Xong.
4. **Chưa làm:** `quy_che` (56 ảnh OCR — chờ `ocr.py`).

### Bug thật tìm thấy khi chạy trên dữ liệu thật (không đoán trước được)

- Gán nhãn `doi_tuong` theo **từng đoạn văn** cho tài liệu không có heading nào (`phu-luc-01/13/15` — văn xuôi liên tục, không đánh số) xé một mạch văn thành hàng chục chunk vô nghĩa (có chunk 2 token, vd chỉ `"Phần B – Các điều khoản bổ sung"`) vì các đoạn liên tiếp xen kẽ nhắc "Người dùng"/"Đối tác" trong một quy trình duy nhất. Sửa: ranh giới `doi_tuong` chỉ áp dụng cho khoản có số thứ tự **thật** của tài liệu (`node.children` khác rỗng); văn bản không đánh số chỉ gom theo kích thước, gán nhãn sau khi đã gom.
- Cụm dẫn nhập cố định ("Đối với Đối Tác", "Nếu Bạn là Người dùng" — dự kiến ở `02-chunking.md`) không khớp cách viết thật (`"4.1. Người dùng phải tuân thủ..."`, `"4.2. Đối tác phải tuân thủ..."`) — đổi sang nhận diện theo **sự có mặt** của "đối tác" / "người dùng"|"khách hàng" trong chính văn bản khoản.

### Kết quả đo thật (18 tài liệu, thay số tạm ở `02-chunking.md`)

337 chunk, không chunk nào vượt 500 token sau khi tách hết có thể; median 142 token, p90 ~453. Riêng FAQ: 52 chunk (49 câu gốc + 3 câu bị tách vì quá dài), median 152, p90 417 — khớp sát số đo cũ (median 160, p90 415) dù tokenizer và pipeline đã đổi.

## Task list: `index` (đã code, 2026-09-22)

Thêm `config/default.toml` + `rag_gsm/config.py` (đọc bằng `tomllib`) thật ở bước này — trước đó chỉ là kế hoạch trong tài liệu này. Cài `sentence-transformers`, `lancedb`, `bm25s`, `torch` — đúng phiên bản đã ghi ở `docs/learning/03-embedding.md`/`04-index.md` (sentence-transformers 6.1.0, torch 2.14.0, lancedb 0.39.0, bm25s 0.3.11), không cần đổi số nào.

1. `embedder.py` — `Bge3Embedder` (bge-m3 qua sentence-transformers, MPS nếu có, `normalize_embeddings=True` để cosine = dot product). Không prefix, đúng chốt Bước 3. ✅ Xong, chưa có test (cần tải trọng số model ~2,27 GB — cùng loại giới hạn với `extractors/general.py` chưa test vì cần mạng).
2. `dense_store.py` — LanceDB, metric cosine, `prefilter=True` tường minh mọi truy vấn có lọc; bảng phẳng (`chunk_id`, `vector`, tất cả field của `Chunk`, `text_embed` = `text_to_index()`) thay vì gói metadata vào 1 cột JSON — để lọc được bằng SQL (`doi_tuong IN (...)`). ✅ Xong, có test (prefilter, similarity = 1 − `_distance`, cách ly public/internal bằng cấu trúc).
3. `bm25_store.py` — bm25s, tách âm tiết bỏ dấu tự viết (`unicodedata` NFD + bỏ ký tự category Mn; `đ`→`d` phải map tay vì không tách được bằng NFD). Lưu `corpus=chunk_ids` khi `save()` để `retrieve()` trả thẳng `chunk_id` thay vì số thứ tự. ✅ Xong, có test.
4. `build.py` — đọc `data/chunks/*.jsonl`, tách theo `audience` (`khach_hang`→`index/public/`, `noi_bo`→`index/internal/`) **trước khi** embed/build — cách ly bằng cấu trúc chứ không chỉ bằng cột lọc, đúng invariant CLAUDE.md. ✅ Xong.

Kiểm tra bằng tay trên dữ liệu thật: câu "hủy chuyến xe có bị trừ tiền không" — BM25 ra `faq#3.6` rồi `faq#2.16` sát nhau (khớp đúng ca hòa điểm đã ghi ở `04-index.md`, dù corpus thật 337 chunk khác corpus thử nghiệm 161 chunk khi viết tài liệu đó).

## Task list: `retrieve` (đã code, 2026-09-22)

Bước 5 và 6 đã brainstorm xong từ trước (`05-retrieval.md`, `06-pageindex-fallback.md`); phần "reorder" của Bước 7 nằm ở `retrieve/reorder.py` theo đúng cây thư mục (phần generation/citation của Bước 7 vẫn thuộc `generate/`, chưa code).

1. `reorder.py` — sandwich reorder, thuần sắp xếp, không phụ thuộc gì. ✅ Xong, có test (khớp đúng ví dụ K=3 trong `07-reorder-generation-citation.md`).
2. `hybrid.py` — RRF (k=60, không trọng số, top-20/nhánh). BM25 (bm25s) không hỗ trợ prefilter theo metadata như LanceDB — đây là một khoảng trống `05-retrieval.md` không nói tới; bù bằng cách lấy dư (top-N × 5) rồi lọc `doi_tuong` sau, chấp nhận được vì bm25s tính điểm chính xác trên toàn bộ từ vựng (không xấp xỉ như ANN) và corpus chỉ vài trăm chunk. ✅ Xong, có test.
3. `rerank.py` — **đổi so với kế hoạch**: xem "Bug thật" dưới đây. ✅ Xong (dùng `AutoModelForSequenceClassification` thay vì `CrossEncoder`), có test cho phần logic (`rerank()`), chưa có test offline cho `VietnameseReranker` thật (cùng lý do `embedder.py`: cần tải model).
4. `fallback.py` — outline (breadcrumb + N ký tự đầu) + `LLMAdapter.generate_json` + kiểm chứng trích dẫn nguyên văn (substring). Chỉ phụ thuộc `LLMAdapter` (Protocol trong `schemas.py`), **không** phụ thuộc `generate/llm_adapter.py` (chưa xây, đúng thứ tự build) — giấu Ollama/Claude sau interface, test bằng LLM giả. ✅ Xong, có test.

### Bug thật tìm thấy khi chạy trên dữ liệu thật: `AITeamVN/Vietnamese_Reranker` không tải được qua `CrossEncoder`

`05-retrieval.md` đã tự ghi rủi ro này trước khi biết kết quả ("Chưa xác nhận `sentence-transformers.CrossEncoder` tải thẳng được AITeamVN/Vietnamese_Reranker không lỗi") — chạy thật xác nhận **đúng là lỗi thật**, không tải được:

- Repo `AITeamVN/Vietnamese_Reranker` chỉ có `sentencepiece.bpe.model` thô, **không có sẵn `tokenizer.json`** (khác `BAAI/bge-reranker-v2-m3`, có cả hai file).
- `transformers` 5.17.0 (đang pin, vì `sentence-transformers` 6.1.0 đòi `transformers>=5,<6`) đoán nhầm file sentencepiece đó là định dạng tiktoken khi tự chuyển đổi sang fast tokenizer — lỗi ngay cả khi đã cài `sentencepiece` và `tiktoken`. Tái hiện được với mọi cách gọi (`AutoTokenizer`, `XLMRobertaTokenizer`, `XLMRobertaTokenizerFast`, có/không `use_fast`).
- Hạ `transformers` xuống `<5` (bản này nạp tokenizer đúng, đã kiểm bằng `uv run --with "transformers<5" --with protobuf`) **không dùng được** vì xung đột cứng với `sentence-transformers` 6.1.0.
- Cách sửa: dùng một môi trường tạm (`uv run --with "transformers<5" --with protobuf`, không đụng dependency chính) convert tokenizer sang `tokenizer.json` một lần, cache theo máy tại `~/.cache/rag_gsm/tokenizer_fix/`; nạp lại bình thường trên `transformers` 5.17.0 sau đó không lỗi (đã kiểm). `rerank.py` tự động chạy bước sửa này khi cần (`_ensure_fixed_tokenizer`), và dùng thẳng `AutoModelForSequenceClassification` + tokenizer đã sửa thay vì `sentence_transformers.CrossEncoder` (không còn "không thêm dependency mới" như dự kiến, nhưng không thêm dependency nào cả — `transformers` vốn đã có sẵn).
- Đã kiểm điểm số ra hợp lý sau khi sửa: câu hỏi "hủy chuyến xe có bị trừ tiền không" với đoạn liên quan cho 0,79 (sigmoid), đoạn không liên quan cho 0,00009.

## Khi nào cập nhật file này

Chỉ khi đổi **hợp đồng** giữa module (thêm/bớt field, đổi kiểu). Đổi số trong `config/default.toml` không cần sửa file này — đó là việc của Bước 9 bake-off.
