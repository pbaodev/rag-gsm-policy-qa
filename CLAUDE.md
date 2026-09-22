# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

All 10 brainstorm docs (`docs/learning/00`–`09`) are done and the module architecture is fixed in `docs/kien-truc-code.md`. Code has started: `ingest` (`rag_gsm/ingest/`) and `chunk` (`rag_gsm/chunk/`) are real, working against live greensm.com data, and produce `data/chunks/*.jsonl` (337 chunks / 18 documents). `index`, `retrieve`, `generate`, `ui`, `eval` are not written yet — their contracts exist as `Protocol`/dataclass stubs in `rag_gsm/schemas.py` but no implementation.

Check `CAPABILITY-MAP.md`'s progress table and `docs/kien-truc-code.md` before assuming a design question is open — most are already decided there, with reasons and rejected alternatives.

## Path gotcha

The project directory is `/Users/baobun/AI20K/LAB-AI20K/RAG Pipeline ` — **with a trailing space**. Quote every path in Bash and keep the trailing space in absolute paths; an unquoted or trimmed `cd` fails with "no such file or directory".

## Commands

```
uv sync                                  # install deps into .venv (Python 3.12 pinned)
uv run pytest                            # run all tests (currently ingest-only, no network)
uv run pytest tests/test_heading.py -v   # run one test file
uv run python -m rag_gsm.ingest.run      # fetch live greensm.com JSON, write data/markdown/*.md
uv run python -m rag_gsm.chunk.run       # read data/markdown/*.md, write data/chunks/<doc_id>.jsonl
```

`data/` and `.venv/` are working state, not committed source — `uv run python -m rag_gsm.ingest.run` regenerates `data/markdown/` from the live site any time; `uv run python -m rag_gsm.chunk.run` regenerates `data/chunks/` from `data/markdown/` (no network needed for this one).

## Working on the learning docs

The docs *are* the deliverable, so their form matters as much as their content.

- Written in **Vietnamese**, one file per step: `docs/learning/NN-<step>.md`, about one page, tables over prose.
- Standard sections: a `## Chốt` table (Việc / Chọn / Vì sao), an options table (Phương án / Ưu / Nhược / Quyết định), `## Không chọn` with a "Khi nào đổi" column, `## Rủi ro và kiểm chứng`, `## Bài học`, `## Tham khảo`.
- **Record the rejected options and why** — they carry as much of the learning as the chosen one, and each one names the condition that would reverse it.
- Brainstorm the step first: options, tradeoffs, a recommendation; the owner decides. Ask only what is genuinely their call. If they answer a question with a question, answer theirs first, then re-derive the recommendation.
- Verify library versions, licenses and behavior against PyPI or the source before recording them. Several decisions here turned on a license (jina → CC-BY-NC) or a token limit, and the docs log cases where a summarizing tool fabricated facts about the corpus.
- After each decision: write/update that step's doc **and** the progress table in `CAPABILITY-MAP.md`.

## Architecture

Six modules, built in dependency order — `ingest` → `index` → `retrieve` → `generate` → `ui`, with `eval` written early and re-run after each one. `CAPABILITY-MAP.md` is the authoritative version of this table.

Query path: dense ∥ BM25 → RRF → rerank → top-1 above threshold? if yes context reorder; if no PageIndex fallback → enough evidence? if no answer "không biết" → LLM → answer + citation → Streamlit with a trace panel.

### Corpus

Vietnamese GSM (Green SM) ride-hailing customer policy, from greensm.com. **Almost everything is clean JSON in the page's `__NEXT_DATA__`, not DOM text** — this was verified wrong once (2026-09-22 correction in `docs/learning/01-ingestion.md`) and fixed; don't reintroduce DOM scraping for pages that already work via JSON. Current shape, 18 documents, ~54k words / ~249k characters of body text (~68k–74k tokens estimated at the word→token ratios `docs/learning/03-embedding.md` already established) — about 1.7× the "~40k token" figure that doc and `06-pageindex-fallback.md` originally used; both have been updated to the real number:

- `dieu-khoan-su-dung` + 15 `phu-luc-NN-*` appendices — all customer-facing (verified by reading each appendix's opening line, not assumed), from `generalTerms.generalItems[]`
- `chinh-sach-du-lieu-ca-nhan` — 14 pre-numbered sections, from the separate `privacyNotice.privacyItems[]` (its near-duplicate `generalItems[12]` is skipped on purpose)
- `bao-hiem-khach-hang` — one table, from `insuranceData` (`columns` is a `"|"`-joined string, `rows` are `{value1, value2, ...}` dicts keyed by position, *not* a list of column objects)
- `faq` — 49 customer Q&A across 6 categories, from `contentFaq.setUpFaq`

Still open: the "E-Green wallet" terms page from the original inventory no longer exists at its documented URL and hasn't been found elsewhere (ingest intentionally does not drop it from scope — see `docs/learning/01-ingestion.md`). "Quy chế hoạt động" (56 JPG page images) still needs OCR, not built yet. `service-agreement` stays excluded (confirmed driver/transport-unit facing, not customer facing). Read `docs/learning/01-ingestion.md` before touching ingestion rather than re-deriving any of this from scratch — it has the exact JSON paths, URLs, and doc_id-to-`generalItems[i]` mapping.

### Locked-in stack

Core logic (RRF, fallback threshold, context reorder, prompt + citation assembly) is hand-written on purpose; libraries only for parsers, embedding, vector store and BM25. **No LangChain, no LlamaIndex.** Fetching is `httpx` reading `__NEXT_DATA__` JSON directly (DOM/`BeautifulSoup` scraping and Crawl4AI are fallbacks for the rare page without JSON, not the main path); conversion/OCR is Docling; embedding is bge-m3 via sentence-transformers (local, MPS); storage is LanceDB (cosine, flat scan, no ANN) plus bm25s; the LLM sits behind a thin adapter (Ollama `qwen3:4b` in dev, Claude API when quality matters). Token counting at chunk time uses the real bge-m3 tokenizer (`transformers.AutoTokenizer`, tokenizer-only — no torch pulled in) rather than a word→token estimate, since `docs/learning/02-chunking.md` already flagged the old estimate as provisional.

### Ingest gotchas (found by running against live data, not guessed)

- **CMS rich-text fields mix in raw HTML.** Some `description`/answer strings contain `<strong>`, `<i>`, `<a href>` inline — inconsistently, not every document uses them for the same thing (e.g. `generalItems[0]`'s headings are bare `"1. TITLE"` lines, but `generalItems[2]`'s are `<strong>1. TITLE</strong>` — lose that and you silently lose that document's top-level headings). `heading.strip_inline_html()` runs before every heading match; call it (or `heading.classify_line`, which already calls it) rather than matching raw JSON strings.
- Line breaks inside these JSON strings are literal `\r\n`, not markdown blank lines — `heading.split_lines()` handles this.
- Don't assume a JSON field's shape from one example; `insuranceData.columns` looked like it should be a list of column defs and was actually a delimited string. Print/inspect the real fetched structure before writing a parser for a new page.

### Chunk gotchas (found by running against live data, not guessed)

- **`doi_tuong` boundaries only make sense at real khoản level.** Applying the label-boundary rule per *paragraph* to documents with no heading numbering at all (`phu-luc-01/13/15` — plain prose, e.g. a step-by-step user flow that naturally alternates "Người dùng làm X" / "Đối tác làm Y" mid-narrative) shredded a single coherent procedure into dozens of near-empty chunks. Fixed in `rules.py`: the label-boundary rule applies only when `node.children` came from real document numbering; headingless text is packed by size only, and `doi_tuong` is assigned *after* packing, for metadata/filtering, not as a hard boundary.
- The introductory phrasing `02-chunking.md` expected the `doi_tuong` regex to key off ("Đối với Đối Tác", "Nếu Bạn là Người dùng") doesn't match how the real clauses are written (`"4.1. Người dùng phải tuân thủ..."`, `"4.2. Đối tác phải tuân thủ..."`). `label_doi_tuong()` instead checks for the *presence* of "đối tác" vs "người dùng"/"khách hàng" in the clause's own text.

### Invariants any implementation must hold

These were each paid for with a measurement or a bug, and they cut across modules:

- **Headings are the contract** between ingest, PageIndex and citation. Build them from the document's own numbering (`1.` / `1.1.` / `1.1.1.`, FAQ group/question), never from what the converter inferred. The PageIndex tree *is* that skeleton.
- **Vietnamese is normalized twice**: NFC right after conversion, and diacritics stripped for BM25 tokenization (one index, syllable tokens — stripping diacritics moved MRR on undiacriticized queries from 0.25 to 0.94; word segmentation did not help and broke those queries).
- **Never threshold an RRF score** — it is rank-based and not comparable to cosine. The fallback threshold reads dense cosine top-1, and it is a property of the embedding model: recalibrate whenever the model changes.
- **Filter before ranking** in LanceDB and pass `prefilter` explicitly; post-filtering silently returns too few rows or none. LanceDB returns `_distance`, so similarity is `1 - _distance`.
- **Isolation by structure, not just by filter**: `index/public/` and `index/internal/` are separate directories, and internal documents (`audience=noi_bo`) are never served to customers. A test must assert the public index leaks nothing internal.
- **`doi_tuong` labelling** (`nguoi_dung` / `doi_tac` / `chung`) is per-clause, because the general terms mix customer and partner obligations. Retrieval for customers takes only `nguoi_dung` and `chung`, and clauses with different labels must not be merged into one chunk.
- **Source trust is a label**, `nguon_tin_cay` (`chinh_thuc` / `bao_chi` / `cong_dong` / `noi_bo`); only official sources are indexed by default.
- **Keep the originals.** `data/raw/` is source of truth, Markdown is derived, so changing converters never means re-crawling or re-OCRing. `content_hash` skips unchanged documents.
- **Chunk ids are stable and citable**: `<doc>#<number>` (`general#3.2`, `faq#3.6`), a merged chunk spans a range (`general#3.2-3.4`). Citation is source URL + heading path, plus page number for image/PDF-derived text.
- **Every parameter needs an eval number**, not a guess — chunk size, k, thresholds, tokenizer, embedding model (bake-off on the GSM question set including one API model as a ceiling). Step 9 should also include a "stuff the whole corpus into the prompt" baseline: the text corpus is only ~40k tokens, so RAG has to earn its place.

### Data layout

```
rag_gsm/schemas.py                Document, Chunk, Embedder/LLMAdapter protocols, etc. — shared contracts, see docs/kien-truc-code.md
rag_gsm/ingest/                   web.py (fetch + __NEXT_DATA__, now also saves raw HTML to data/raw/web/), heading.py, normalize.py, extractors/{general,privacy,insurance,faq}.py, run.py
rag_gsm/chunk/                    loader.py (read data/markdown/*.md back into Document), rules.py, run.py
data/raw/{web,images,internal}/   originals — web/ populated (4 HTML files) by ingest/web.py; images/ and internal/ not populated yet (no OCR, no internal docs yet)
data/markdown/<doc_id>.md         derived, with YAML front matter (source, doc_type, audience, nguon_tin_cay, fetched_at, content_hash, ngay_hieu_luc) — regenerate with `uv run python -m rag_gsm.ingest.run`
data/chunks/<doc_id>.jsonl        chunker output, index input — regenerate with `uv run python -m rag_gsm.chunk.run` (337 chunks / 18 documents as of 2026-09-22)
index/public/{lancedb,bm25}/      dense table + BM25 index — not built yet
```

## Known loose ends

- OCR pipeline for "Quy chế hoạt động" (56 images, needs Docling + an OCR-engine bake-off per `docs/learning/01-ingestion.md`) — not started.
- "Điều khoản ví E-Green" — page not found at its documented URL nor inside `generalItems`; still unresolved.
- Whether/how to index the 3,774 news articles — not decided.
- The 14-section privacy notice (`chinh-sach-du-lieu-ca-nhan`) mixes many subject categories (customers, staff, shareholders, partners) that don't map cleanly onto the `nguoi_dung`/`doi_tac`/`chung` split `doi_tuong` labelling was designed for (that split is really about "Quy định chung" mixing customer vs. partner *obligations*). `chunk_dieu_khoan()` still runs the same regex on it; spot-check its labelling before trusting it for retrieval filtering.
