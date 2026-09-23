"""Buoc 8: Streamlit chat + trace panel (docs/learning/08-streamlit-ui.md).
Chay: uv run streamlit run rag_gsm/ui/app.py

Single-turn (Buoc 7 da chot): session_state["messages"] chi de HIEN THI
lai chat thread, khong dung lam ngu canh truy hoi cho cau hoi tiep theo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# `streamlit run <file>` execute file nay truc tiep, khong dam bao thu
# muc goc du an (chua package rag_gsm) nam san trong sys.path nhu khi
# chay qua `python -m` - tu them de import duoi day luon hoat dong bat
# ke duoc goi the nao (bug that: ModuleNotFoundError khi chi dua vao
# editable install qua pyproject.toml, xem CLAUDE.md "UI gotchas").

import streamlit as st

from rag_gsm.config import load_config
from rag_gsm.generate.answer import generate_answer
from rag_gsm.generate.llm_adapter import build_llm_adapter
from rag_gsm.generate.prompt import build_prompt
from rag_gsm.index.bm25_store import load_bm25_index
from rag_gsm.index.build import load_all_chunks
from rag_gsm.index.dense_store import open_table
from rag_gsm.index.embedder import Bge3Embedder
from rag_gsm.retrieve.pipeline import retrieve_with_fallback
from rag_gsm.retrieve.rerank import VietnameseReranker
from rag_gsm.schemas import RetrievalCandidate, RetrievalResult

PUBLIC_INDEX_DIR = Path("index") / "public"


@st.cache_resource
def load_resources() -> dict:
    """Tai nguyen nang dung chung moi phien - st.cache_resource (khong
    phai cache_data, vi model/ket noi khong serialize duoc) (08-*.md)."""
    config = load_config()
    chunk_lookup = {c.chunk_id: c for c in load_all_chunks() if c.audience == "khach_hang"}
    table = open_table(PUBLIC_INDEX_DIR / "lancedb")
    bm25_index = load_bm25_index(PUBLIC_INDEX_DIR / "bm25")
    embedder = Bge3Embedder(model_name=config.embedding.model)
    reranker = VietnameseReranker(model_name=config.rerank.model)
    llm = build_llm_adapter(config.generation.model, temperature=config.generation.temperature)
    return {
        "config": config,
        "chunk_lookup": chunk_lookup,
        "table": table,
        "bm25_index": bm25_index,
        "embedder": embedder,
        "reranker": reranker,
        "llm": llm,
    }


def _candidate_rows(candidates: list[RetrievalCandidate]) -> list[dict]:
    return [
        {
            "chunk_id": c.chunk_id,
            "dense_rank": c.dense_rank,
            "dense_score": c.dense_score,
            "bm25_rank": c.bm25_rank,
            "bm25_score": c.bm25_score,
            "rrf_score": c.rrf_score,
            "rerank_score": c.rerank_score,
        }
        for c in candidates
    ]


def render_trace(retrieval: RetrievalResult, query: str, chunk_lookup: dict) -> None:
    """Chi ve lai DUNG du lieu retrieval/trace da co (da loc doi_tuong/
    audience tu pipeline that) - khong query lai khong loc "cho dep",
    dung invariant "an toan bang cau truc" da lap lai xuyen suot du an."""
    trace = retrieval.trace
    with st.expander("Xem trace"):
        st.markdown(f"**Nhánh:** `{trace.branch}` · **Ngưỡng rerank:** {trace.threshold}")

        if trace.latency_ms:
            total_ms = sum(trace.latency_ms.values())
            st.markdown(f"**Độ trễ:** {trace.latency_ms} — tổng **{total_ms:.0f} ms**")

        if trace.candidates_before_rerank:
            st.markdown("**Trước rerank** (dense ∥ BM25 → RRF):")
            st.dataframe(_candidate_rows(trace.candidates_before_rerank), hide_index=True)

        if trace.candidates_after_rerank:
            st.markdown("**Sau rerank:**")
            st.dataframe(_candidate_rows(trace.candidates_after_rerank), hide_index=True)

        if trace.fallback_node_list is not None:
            st.markdown(f"**PageIndex fallback** — outline gửi {trace.fallback_outline_size} mục:")
            st.json(trace.fallback_node_list)

        if trace.citation_map:
            rows = []
            for n, chunk_id in sorted(trace.citation_map.items()):
                chunk = chunk_lookup.get(chunk_id)
                rows.append(
                    {
                        "n": n,
                        "chunk_id": chunk_id,
                        "heading_path": chunk.heading_path if chunk else "",
                        "source": chunk.source if chunk else "",
                    }
                )
            st.markdown("**Trích dẫn:**")
            st.dataframe(rows, hide_index=True)

        if retrieval.chunks:
            with st.expander("Xem prompt đầy đủ gửi LLM", expanded=False):
                system, user, _ = build_prompt(query, retrieval.chunks)
                st.text(f"SYSTEM:\n{system}\n\nUSER:\n{user}")


def main() -> None:
    st.set_page_config(page_title="GSM RAG", page_icon="🚕")
    st.title("Trợ lý chính sách Green SM")

    resources = load_resources()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("retrieval") is not None:
                render_trace(msg["retrieval"], msg["query"], resources["chunk_lookup"])

    query = st.chat_input("Hỏi gì đó về chính sách Green SM...")
    if not query:
        return

    st.session_state["messages"].append({"role": "user", "content": query, "retrieval": None, "query": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Đang tra cứu..."):
                retrieval = retrieve_with_fallback(
                    query,
                    embedder=resources["embedder"],
                    table=resources["table"],
                    bm25_index=resources["bm25_index"],
                    chunk_lookup=resources["chunk_lookup"],
                    reranker=resources["reranker"],
                    llm=resources["llm"],
                    config=resources["config"],
                )
                answer = generate_answer(query, retrieval, resources["llm"], resources["chunk_lookup"])
        except Exception as e:  # noqa: BLE001 - loi model/mang khong duoc lam mat lich su phien (08-*.md)
            error_text = f"Xin lỗi, có lỗi khi xử lý câu hỏi này: {e}"
            st.error(error_text)
            st.session_state["messages"].append(
                {"role": "assistant", "content": error_text, "retrieval": None, "query": query}
            )
        else:
            st.write(answer.text)
            render_trace(retrieval, query, resources["chunk_lookup"])
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer.text, "retrieval": retrieval, "query": query}
            )


if __name__ == "__main__":
    main()
