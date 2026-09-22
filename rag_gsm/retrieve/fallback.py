"""PageIndex fallback (Buoc 6), tu viet - khong dung thu vien `pageindex`
cua VectifyAI (doc thay o 06-pageindex-fallback.md). Mot luot goi LLM voi
outline toan bo (da loc doi_tuong/audience) + cau hoi; bat LLM trich
nguyen van tu chunk da chon de kiem chung (grounding) truoc khi coi la
du bang chung - tra loi sai chinh sach nguy hiem hon "khong biet".

Chi phu thuoc `LLMAdapter` (Protocol trong schemas.py), khong phu thuoc
`generate/llm_adapter.py` (module chua xay, se lam sau theo dung thu tu
build ingest -> index -> retrieve -> generate) - giau chi tiet Ollama/
Claude sau interface, giong nguyen tac da lap lai o Embedder/CrossEncoder.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_gsm.schemas import Chunk, LLMAdapter

DEFAULT_EXCERPT_CHARS = 200
DEFAULT_DOI_TUONG_ALLOW = ("nguoi_dung", "chung")

SYSTEM_PROMPT = (
    "Ban la tro ly tra cuu chinh sach Green SM. Duoc cho mot danh sach muc "
    "(outline) va mot cau hoi. Chon (cac) muc lien quan nhat de tra loi, va "
    "TRICH NGUYEN VAN mot cau tu chinh muc do lam bang chung - khong duoc "
    "dien giai lai. Neu khong muc nao lien quan, tra ve node_list rong. "
    'Tra ve dung JSON: {"reasoning": "...", "node_list": '
    '[{"chunk_id": "...", "trich_dan": "..."}]}'
)


@dataclass
class FallbackResult:
    node_list: list[dict]  # da qua grounding check: [{chunk_id, trich_dan}]
    reasoning: str
    du_bang_chung: bool


def build_outline(chunks: list[Chunk], *, excerpt_chars: int = DEFAULT_EXCERPT_CHARS) -> list[dict]:
    return [
        {"chunk_id": c.chunk_id, "breadcrumb": c.breadcrumb, "doan_trich": c.text[:excerpt_chars]}
        for c in chunks
    ]


def _format_outline(outline: list[dict]) -> str:
    return "\n".join(f"- {e['chunk_id']} | {e['breadcrumb']} | {e['doan_trich']}" for e in outline)


def _is_grounded(trich_dan: str, chunk_text: str) -> bool:
    return bool(trich_dan and trich_dan.strip()) and trich_dan.strip() in chunk_text


def run_fallback(
    query: str,
    chunks: list[Chunk],
    llm: LLMAdapter,
    *,
    doi_tuong_allow: tuple[str, ...] = DEFAULT_DOI_TUONG_ALLOW,
    excerpt_chars: int = DEFAULT_EXCERPT_CHARS,
) -> FallbackResult:
    allowed = [c for c in chunks if c.doi_tuong in doi_tuong_allow]
    chunk_lookup = {c.chunk_id: c for c in allowed}
    outline = build_outline(allowed, excerpt_chars=excerpt_chars)

    user_prompt = f"Outline:\n{_format_outline(outline)}\n\nCau hoi: {query}"
    raw = llm.generate_json(
        SYSTEM_PROMPT,
        user_prompt,
        schema_hint='{"reasoning": str, "node_list": [{"chunk_id": str, "trich_dan": str}]}',
    )

    reasoning = raw.get("reasoning", "")
    grounded_nodes = []
    for node in raw.get("node_list") or []:
        chunk = chunk_lookup.get(node.get("chunk_id"))
        if chunk is not None and _is_grounded(node.get("trich_dan", ""), chunk.text):
            grounded_nodes.append(node)

    return FallbackResult(
        node_list=grounded_nodes,
        reasoning=reasoning,
        du_bang_chung=len(grounded_nodes) > 0,
    )
