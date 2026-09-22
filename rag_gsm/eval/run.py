"""CLI: uv run python -m rag_gsm.eval.run [config_id] [limit] - chay bo
cau hoi vang qua pipeline that: do retrieval o 4 tang (dense/BM25/RRF/
rerank), do do chinh xac quyet dinh nhanh, va LLM-judge (Claude, chi chay
neu co ANTHROPIC_API_KEY). Ghi eval/runs/<config_id>.jsonl (Buoc 9)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rag_gsm.config import load_config
from rag_gsm.eval.golden import load_golden_questions
from rag_gsm.eval.judge import DEFAULT_JUDGE_MODEL, judge_answer
from rag_gsm.eval.metrics import mrr, recall_at_k
from rag_gsm.generate.answer import generate_answer
from rag_gsm.generate.llm_adapter import ClaudeAdapter, build_llm_adapter
from rag_gsm.index.bm25_store import load_bm25_index
from rag_gsm.index.build import load_all_chunks
from rag_gsm.index.dense_store import open_table
from rag_gsm.index.embedder import Bge3Embedder
from rag_gsm.retrieve.hybrid import hybrid_search
from rag_gsm.retrieve.pipeline import retrieve_with_fallback
from rag_gsm.retrieve.rerank import VietnameseReranker
from rag_gsm.retrieve.rerank import rerank as rerank_fn
from rag_gsm.schemas import RetrievalCandidate

PUBLIC_INDEX_DIR = Path("index") / "public"
RUNS_DIR = Path("eval") / "runs"
RECALL_K = 5


def _layer_order(candidates: list[RetrievalCandidate], rank_attr: str) -> list[str]:
    ranked = sorted(
        (c for c in candidates if getattr(c, rank_attr) is not None), key=lambda c: getattr(c, rank_attr)
    )
    return [c.chunk_id for c in ranked]


def _layer_metrics(gold_chunk_ids: list[str], ordered_ids: list[str]) -> dict:
    return {"recall": recall_at_k(gold_chunk_ids, ordered_ids, RECALL_K), "mrr": mrr(gold_chunk_ids, ordered_ids)}


def _run_one(q, *, config, embedder, table, bm25_index, chunk_lookup, reranker, llm, judge_llm) -> dict:
    if not q.gold_chunk_ids:
        retrieval_metrics = None
    else:
        candidates = hybrid_search(
            q.cau_hoi,
            embedder=embedder,
            table=table,
            bm25_index=bm25_index,
            chunk_lookup=chunk_lookup,
            top_n_per_branch=config.rrf.top_n_per_branch,
            rrf_k=config.rrf.k,
        )
        reranked = rerank_fn(
            q.cau_hoi, candidates, chunk_lookup, reranker, top_k_into_rerank=config.rerank.top_k_into_rerank
        )
        retrieval_metrics = {
            "dense": _layer_metrics(q.gold_chunk_ids, _layer_order(candidates, "dense_rank")),
            "bm25": _layer_metrics(q.gold_chunk_ids, _layer_order(candidates, "bm25_rank")),
            "rrf": _layer_metrics(q.gold_chunk_ids, [c.chunk_id for c in candidates]),
            "rerank": _layer_metrics(q.gold_chunk_ids, [c.chunk_id for c in reranked]),
        }

    retrieval = retrieve_with_fallback(
        q.cau_hoi,
        embedder=embedder,
        table=table,
        bm25_index=bm25_index,
        chunk_lookup=chunk_lookup,
        reranker=reranker,
        llm=llm,
        config=config,
    )
    answer = generate_answer(q.cau_hoi, retrieval, llm, chunk_lookup)
    branch_match = answer.branch == q.nhanh_ky_vong

    verdict = judge_answer(q, answer, judge_llm) if judge_llm is not None else None

    top_rerank_score = (
        retrieval.trace.candidates_after_rerank[0].rerank_score
        if retrieval.trace.candidates_after_rerank
        else None
    )

    row = {
        "question_id": q.id,
        "cau_hoi": q.cau_hoi,
        "chu_de": q.chu_de,
        "do_kho": q.do_kho,
        "nhanh_ky_vong": q.nhanh_ky_vong,
        "nhanh_thuc_te": answer.branch,
        "branch_match": branch_match,
        "top_rerank_score": top_rerank_score,
        "rerank_pass_threshold": config.thresholds.rerank_pass,
        "fallback_node_list": retrieval.trace.fallback_node_list,
        "retrieval_metrics": retrieval_metrics,
        "answer_text": answer.text,
        "verdict": verdict.__dict__ if verdict else None,
    }

    rerank_recall = retrieval_metrics["rerank"]["recall"] if retrieval_metrics else None
    recall_str = f"{rerank_recall:.2f}" if rerank_recall is not None else "n/a"
    score_str = f"{top_rerank_score:.3f}" if top_rerank_score is not None else "n/a"
    print(
        f"{q.id}: nhanh {answer.branch} "
        f"({'khop' if branch_match else 'LECH'} voi ky vong {q.nhanh_ky_vong}), "
        f"recall@{RECALL_K} sau rerank={recall_str}, diem rerank top-1={score_str}",
        flush=True,
    )
    return row


def main() -> None:
    config_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    config = load_config()
    questions = load_golden_questions()
    if limit:
        questions = questions[:limit]

    chunk_lookup = {c.chunk_id: c for c in load_all_chunks() if c.audience == "khach_hang"}
    table = open_table(PUBLIC_INDEX_DIR / "lancedb")
    bm25_index = load_bm25_index(PUBLIC_INDEX_DIR / "bm25")
    embedder = Bge3Embedder(model_name=config.embedding.model)
    reranker = VietnameseReranker(model_name=config.rerank.model)
    llm = build_llm_adapter(config.generation.model, temperature=config.generation.temperature)

    judge_llm = None
    try:
        judge_llm = ClaudeAdapter(DEFAULT_JUDGE_MODEL, temperature=0.0)
    except RuntimeError as e:
        print(f"[eval] Judge tat: {e} - chi do retrieval + nhanh, khong cham noi dung answer.")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUNS_DIR / f"{config_id}.jsonl"

    rows = []
    with out_path.open("w", encoding="utf-8") as out_file:
        for q in questions:
            try:
                row = _run_one(
                    q,
                    config=config,
                    embedder=embedder,
                    table=table,
                    bm25_index=bm25_index,
                    chunk_lookup=chunk_lookup,
                    reranker=reranker,
                    llm=llm,
                    judge_llm=judge_llm,
                )
            except Exception as e:  # noqa: BLE001 - mot cau loi/timeout khong duoc lam sap ca batch
                row = {
                    "question_id": q.id,
                    "cau_hoi": q.cau_hoi,
                    "chu_de": q.chu_de,
                    "do_kho": q.do_kho,
                    "nhanh_ky_vong": q.nhanh_ky_vong,
                    "nhanh_thuc_te": None,
                    "branch_match": False,
                    "loi": f"{type(e).__name__}: {e}",
                }
                print(f"{q.id}: LOI - {row['loi']}", flush=True)

            rows.append(row)
            out_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            out_file.flush()

    n = len(rows)
    errors = [r for r in rows if r.get("loi")]
    branch_acc = sum(r["branch_match"] for r in rows) / n if n else 0.0
    scored = [r for r in rows if r.get("retrieval_metrics")]
    avg_recall = sum(r["retrieval_metrics"]["rerank"]["recall"] for r in scored) / len(scored) if scored else 0.0
    avg_mrr = sum(r["retrieval_metrics"]["rerank"]["mrr"] for r in scored) / len(scored) if scored else 0.0
    print(
        f"\nTong: {n} cau ({len(errors)} loi/timeout). Do chinh xac nhanh: {branch_acc:.2%}. "
        f"Recall@{RECALL_K} sau rerank: {avg_recall:.2%} (tren {len(scored)} cau co gold_chunk_ids). "
        f"MRR sau rerank: {avg_mrr:.2f}."
    )
    print(f"Ghi: {out_path}")


if __name__ == "__main__":
    main()
