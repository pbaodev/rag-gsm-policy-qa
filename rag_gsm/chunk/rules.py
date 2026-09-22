"""Quy tac gom/tach chunk theo nhom tai lieu (Buoc 2).

Dau vao: Document + than Markdown (sau front matter) tu ingest. Ranh gioi
chunk lay tu heading ma ingest da dung (`#`/`##`/`###`), khong doan lai
cau truc o day - chunk chi quyet dinh RANH GIOI, khong quyet dinh HEADING
(xem docs/kien-truc-code.md).

Thuat toan chung, dung cho ca dieu_khoan/chinh_sach lan FAQ/bang:
1. Dung cay tu heading `#`/`##`/`###` cua file Markdown (build_tree).
2. Voi moi nhom cap 1 (mot H1, hoac phan "Mo dau" truoc H1 dau tien, hoac
   toan van neu tai lieu khong co heading nao - vd Phu luc 1/13/15):
   - dieu_khoan/chinh_sach: thu ca nhom lam 1 chunk neu vua ngan sach VA
     khong tron doi_tuong; neu khong, gom cac khoan cap 2 LIEN TIEP CUNG
     doi_tuong toi ngan sach (khong bao gio gom khac doi_tuong vao 1 chunk).
   - faq: moi cau hoi (H2) la 1 chunk co dinh, chi TACH (khong gom) khi
     vuot ngan sach.
   - bao_hiem: ca bang la 1 chunk.

Nhan doi_tuong: ban dau du kien theo cum co dinh ("Doi voi Doi Tac", "Neu
Ban la Nguoi dung" - xem docs/learning/02-chunking.md) nhung du lieu that
khong viet theo khuon do (vd "4.1. Nguoi dung phai tuan thu...", "4.2. Doi
tac phai tuan thu..." - xem phu-luc-02-quy-che-car.md). Sua theo du lieu
that: dua vao SU CO MAT cua "doi tac" / "nguoi dung"|"khach hang" trong
chinh van ban khoan, khong dua vao cum dan nhap co dinh.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag_gsm.schemas import Chunk, Document

BUDGET_TOKENS = 500

_HEADING_RE = re.compile(r"^(#{1,3})\s+(?:(\d+(?:\.\d+){0,2})\.\s+)?(.*)$")
_DOI_TAC_RE = re.compile(r"đối\s*tác", re.IGNORECASE)
_NGUOI_DUNG_RE = re.compile(r"(người\s*dùng|khách\s*hàng)", re.IGNORECASE)

_tokenizer = None


def count_tokens(text: str) -> int:
    """Dem token bang tokenizer that cua bge-m3 (Buoc 3 da chot model nay) -
    khong dung uoc luong tu/token, vi 02-chunking.md da ghi ro so do cu
    (do tren generalItems[0]) la tam va se do lai khi code chunk that."""
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
    return len(_tokenizer.encode(text, add_special_tokens=False))


def label_doi_tuong(text: str) -> str:
    has_doi_tac = bool(_DOI_TAC_RE.search(text))
    has_nguoi_dung = bool(_NGUOI_DUNG_RE.search(text))
    if has_doi_tac and not has_nguoi_dung:
        return "doi_tac"
    if has_nguoi_dung and not has_doi_tac:
        return "nguoi_dung"
    return "chung"


@dataclass
class Node:
    level: int
    so_muc: str | None
    title: str
    text: str = ""
    children: list["Node"] = field(default_factory=list)


@dataclass
class DocTree:
    preamble: str
    children: list[Node]


def build_tree(body_markdown: str) -> DocTree:
    """Dung cay tu cac dong '#'/'##'/'###' - do sau cay = so luong '#',
    khong gia dinh H1 luon co mat (vd phu-luc-07 chi co H2, khong co H1 -
    "DIEU N." khong khop khuon so ma heading.py nhan, phat hien khi doc
    du lieu that; chunk van chay dung vi khong doan lai cap cha)."""
    top_children: list[Node] = []
    stack: list[Node] = []
    preamble_lines: list[str] = []
    text_buf: list[str] = []

    def flush_text() -> None:
        text = "\n".join(text_buf).strip()
        text_buf.clear()
        if stack:
            stack[-1].text = f"{stack[-1].text}\n\n{text}".strip() if stack[-1].text else text
        elif text:
            preamble_lines.append(text)

    for line in body_markdown.split("\n"):
        m = _HEADING_RE.match(line)
        if not m:
            text_buf.append(line)
            continue
        flush_text()
        level, so_muc, title = len(m.group(1)), m.group(2), m.group(3).strip()
        node = Node(level=level, so_muc=so_muc, title=title)
        while stack and stack[-1].level >= level:
            stack.pop()
        (stack[-1].children if stack else top_children).append(node)
        stack.append(node)
    flush_text()
    return DocTree(preamble="\n\n".join(preamble_lines), children=top_children)


def _own_text(node: Node) -> str:
    head = None
    if node.so_muc and node.title:
        head = f"{node.so_muc}. {node.title}"
    elif node.title:
        head = node.title
    if head and node.text:
        return f"{head}\n\n{node.text}"
    return node.text or head or ""


def subtree_text(node: Node) -> str:
    parts = [_own_text(node)] + [subtree_text(c) for c in node.children]
    return "\n\n".join(p for p in parts if p)


def get_leaves(node: Node) -> list[Node]:
    """Don vi nho nhat da co san: con H2/H3 neu co, khong thi tach doan
    van cua chinh node (dung cho tai lieu khong co heading nao, vd
    Phu luc 1/13/15 - "nhu dieu khoan neu co danh so, khong thi theo
    doan", cung mot nguyen tac cho ca OCR lan cac Phu luc nay)."""
    if node.children:
        return node.children
    paras = [p.strip() for p in node.text.split("\n\n") if p.strip()]
    if len(paras) <= 1:
        return [node]
    parent_so_muc = node.so_muc
    return [
        Node(
            level=node.level + 1,
            so_muc=f"{parent_so_muc}.p{i}" if parent_so_muc else f"p{i}",
            title="",
            text=p,
        )
        for i, p in enumerate(paras, start=1)
    ]


def top_level_groups(tree: DocTree) -> list[Node]:
    """Nhom cap 1 de chunk: neu co mo dau dang ke (vd doan gioi thieu
    truoc '# 1. DINH NGHIA' trong dieu-khoan-su-dung.md, hoac toan bo
    tai lieu khong co heading nao), coi la 1 nhom "Mo dau" dung truoc."""
    groups: list[Node] = []
    if tree.preamble.strip():
        groups.append(Node(level=1, so_muc=None, title="Mở đầu", text=tree.preamble))
    groups.extend(tree.children)
    return groups


def _pack_texts(paras: list[str], budget: int) -> list[str]:
    pieces: list[str] = []
    bucket: list[str] = []
    bucket_tokens = 0
    for p in paras:
        t = count_tokens(p)
        if t > budget:
            if bucket:
                pieces.append("\n\n".join(bucket))
                bucket, bucket_tokens = [], 0
            pieces.extend(_split_by_sentence(p, budget))
            continue
        if bucket and bucket_tokens + t > budget:
            pieces.append("\n\n".join(bucket))
            bucket, bucket_tokens = [], 0
        bucket.append(p)
        bucket_tokens += t
    if bucket:
        pieces.append("\n\n".join(bucket))
    return pieces


def _split_by_sentence(text: str, budget: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    pieces: list[str] = []
    bucket: list[str] = []
    bucket_tokens = 0
    for s in sentences:
        t = count_tokens(s)
        if bucket and bucket_tokens + t > budget:
            pieces.append(" ".join(bucket))
            bucket, bucket_tokens = [], 0
        bucket.append(s)
        bucket_tokens += t
    if bucket:
        pieces.append(" ".join(bucket))
    return pieces or [text]


def _breadcrumb(root: str, group: Node, leaves: list[Node]) -> str:
    parts = [root]
    if group.title:
        parts.append(f"{group.so_muc}. {group.title}" if group.so_muc else group.title)
    if len(leaves) == 1 and leaves[0] is group:
        pass  # nhom chi co 1 leaf la chinh no - khoi lap lai cung 1 doan
    elif len(leaves) == 1:
        leaf = leaves[0]
        if leaf.title:
            parts.append(f"{leaf.so_muc}. {leaf.title}" if leaf.so_muc else leaf.title)
        elif leaf.so_muc:
            parts.append(leaf.so_muc)
    else:
        parts.append(f"{leaves[0].so_muc}-{leaves[-1].so_muc}")
    return " › ".join(parts)


def _build_chunk(
    doc: Document,
    *,
    so_muc: str | None,
    parent_so_muc: str | None,
    breadcrumb: str,
    text: str,
    doi_tuong: str,
    loai_chunk: str,
) -> Chunk:
    chunk_id = f"{doc.doc_id}#{so_muc}" if so_muc else doc.doc_id
    parent_id = f"{doc.doc_id}#{parent_so_muc}" if parent_so_muc else None
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc.doc_id,
        parent_id=parent_id,
        doc_type=doc.doc_type,
        heading_path=breadcrumb,
        breadcrumb=breadcrumb,
        text=text,
        so_muc=so_muc,
        doi_tuong=doi_tuong,
        audience=doc.audience,
        nguon_tin_cay=doc.nguon_tin_cay,
        ngay_hieu_luc=doc.ngay_hieu_luc,
        trang_bat_dau=None,
        trang_ket_thuc=None,
        loai_chunk=loai_chunk,
        source=doc.source,
        token_count=count_tokens(text),
    )


def _make_chunk_from_leaves(
    doc: Document, root: str, group: Node, leaves: list[Node], doi_tuong: str
) -> Chunk:
    first_so_muc = leaves[0].so_muc or "1"
    last_so_muc = leaves[-1].so_muc or "1"
    so_muc = first_so_muc if len(leaves) == 1 else f"{first_so_muc}-{last_so_muc}"
    text = "\n\n".join(subtree_text(l) for l in leaves)
    breadcrumb = _breadcrumb(root, group, leaves)
    return _build_chunk(
        doc,
        so_muc=so_muc,
        parent_so_muc=group.so_muc,
        breadcrumb=breadcrumb,
        text=text,
        doi_tuong=doi_tuong,
        loai_chunk="dieu_khoan",
    )


def _split_oversized_leaf(doc: Document, root: str, group: Node, leaf: Node, doi_tuong: str) -> list[Chunk]:
    if leaf.children:
        return chunk_dieu_khoan_group(doc, root, leaf)
    paras = [p for p in subtree_text(leaf).split("\n\n") if p.strip()]
    pieces = _pack_texts(paras, BUDGET_TOKENS)
    chunks = []
    for i, piece in enumerate(pieces):
        suffix = chr(ord("a") + i)
        so_muc = f"{leaf.so_muc}-{suffix}" if leaf.so_muc else None
        breadcrumb = _breadcrumb(root, group, [leaf])
        chunks.append(
            _build_chunk(
                doc,
                so_muc=so_muc,
                parent_so_muc=group.so_muc,
                breadcrumb=breadcrumb,
                text=piece,
                doi_tuong=doi_tuong,
                loai_chunk="dieu_khoan",
            )
        )
    return chunks


def chunk_dieu_khoan_group(doc: Document, root: str, group: Node) -> list[Chunk]:
    """1 nhom cap 1 (hoac 1 khoan qua kho phai xu ly de quy). Uu tien
    giu ca nhom lam 1 chunk neu vua ngan sach VA khong tron doi_tuong;
    khong thi gom khoan lien tiep cung doi_tuong (khong bao gio tron).

    Ranh gioi doi_tuong CHI ap dung khi leaf la khoan that (co so thu tu
    tai lieu tu dat, node.children khac rong). Voi tai lieu/doan khong co
    danh so (vd phu-luc-01/13/15 - toan van xuoi, hoac doan mo dau truoc
    H1 dau tien) khong co "khoan" nao de ton trong ranh gioi - ap dung
    doi_tuong theo tung doan se xe vun mot mach tu lien tuc (phat hien khi
    chay tren du lieu that: phu-luc-01 ra 34 chunk, co chunk 2 token)."""
    leaves = get_leaves(group)
    if not group.children:
        return _pack_by_size_only(doc, root, group, leaves)

    labels = [label_doi_tuong(subtree_text(l)) for l in leaves]
    whole_text = subtree_text(group)
    if len(set(labels)) <= 1 and count_tokens(whole_text) <= BUDGET_TOKENS:
        return [_make_chunk_from_leaves(doc, root, group, leaves, labels[0])]

    chunks: list[Chunk] = []
    i = 0
    while i < len(leaves):
        label = labels[i]
        run: list[Node] = [leaves[i]]
        i += 1
        while i < len(leaves) and labels[i] == label:
            run.append(leaves[i])
            i += 1
        chunks.extend(_pack_run(doc, root, group, run, label))
    return chunks


def _pack_by_size_only(doc: Document, root: str, group: Node, leaves: list[Node]) -> list[Chunk]:
    """Gom theo kich thuoc, khong ngat theo doi_tuong (khong co khoan
    that de ton trong ranh gioi) - gan doi_tuong SAU khi gom, tren chinh
    van ban da gop."""
    chunks: list[Chunk] = []
    bucket: list[Node] = []
    bucket_tokens = 0

    def flush() -> None:
        if not bucket:
            return
        label = label_doi_tuong("\n\n".join(subtree_text(l) for l in bucket))
        chunks.append(_make_chunk_from_leaves(doc, root, group, list(bucket), label))
        bucket.clear()

    for leaf in leaves:
        t = count_tokens(subtree_text(leaf))
        if t > BUDGET_TOKENS:
            flush()
            bucket_tokens = 0
            chunks.extend(_split_oversized_leaf(doc, root, group, leaf, label_doi_tuong(subtree_text(leaf))))
            continue
        if bucket and bucket_tokens + t > BUDGET_TOKENS:
            flush()
            bucket_tokens = 0
        bucket.append(leaf)
        bucket_tokens += t
    flush()
    return chunks


def _pack_run(doc: Document, root: str, group: Node, run: list[Node], label: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    bucket: list[Node] = []
    bucket_tokens = 0
    for leaf in run:
        t = count_tokens(subtree_text(leaf))
        if t > BUDGET_TOKENS:
            if bucket:
                chunks.append(_make_chunk_from_leaves(doc, root, group, bucket, label))
                bucket, bucket_tokens = [], 0
            chunks.extend(_split_oversized_leaf(doc, root, group, leaf, label))
            continue
        if bucket and bucket_tokens + t > BUDGET_TOKENS:
            chunks.append(_make_chunk_from_leaves(doc, root, group, bucket, label))
            bucket, bucket_tokens = [], 0
        bucket.append(leaf)
        bucket_tokens += t
    if bucket:
        chunks.append(_make_chunk_from_leaves(doc, root, group, bucket, label))
    return chunks


def chunk_dieu_khoan(doc: Document, body_markdown: str) -> list[Chunk]:
    tree = build_tree(body_markdown)
    chunks: list[Chunk] = []
    for group in top_level_groups(tree):
        chunks.extend(chunk_dieu_khoan_group(doc, doc.title, group))
    return chunks


def chunk_faq(doc: Document, body_markdown: str) -> list[Chunk]:
    """Moi cau hoi (H2) la 1 chunk co dinh; chi tach (khong gom) khi vuot
    ngan sach. FAQ da duoc loc "Danh cho nguoi dung" luc ingest nen gan
    doi_tuong=nguoi_dung thang, khong chay regex (tranh nham khi cau tra
    loi nhac toi "Doi tac" o ngu canh khac, vd huong dan lien he)."""
    tree = build_tree(body_markdown)
    root = "Trung tâm giải đáp"
    chunks: list[Chunk] = []
    for category in tree.children:
        for question in category.children:
            text = _own_text(question)
            if count_tokens(text) <= BUDGET_TOKENS:
                breadcrumb = _breadcrumb(root, category, [question])
                chunks.append(
                    _build_chunk(
                        doc,
                        so_muc=question.so_muc,
                        parent_so_muc=category.so_muc,
                        breadcrumb=breadcrumb,
                        text=text,
                        doi_tuong="nguoi_dung",
                        loai_chunk="faq",
                    )
                )
                continue
            pieces = _pack_texts([p for p in text.split("\n\n") if p.strip()], BUDGET_TOKENS)
            breadcrumb = _breadcrumb(root, category, [question])
            for i, piece in enumerate(pieces):
                suffix = chr(ord("a") + i)
                chunks.append(
                    _build_chunk(
                        doc,
                        so_muc=f"{question.so_muc}-{suffix}",
                        parent_so_muc=category.so_muc,
                        breadcrumb=breadcrumb,
                        text=piece,
                        doi_tuong="nguoi_dung",
                        loai_chunk="faq",
                    )
                )
    return chunks


def _row_to_sentence(col_labels: list[str], row_cells: list[str]) -> str:
    parts = [f"{label}: {value}" for label, value in zip(col_labels, row_cells) if value]
    return "; ".join(parts) + "."


def chunk_bao_hiem(doc: Document, body_markdown: str) -> list[Chunk]:
    """Ca bang la 1 chunk (nho); them ban viet tung hang thanh cau de
    embed/BM25 nam ngay hieu duoc noi dung, khong chi dua vao bang Markdown."""
    lines = [ln for ln in body_markdown.split("\n") if ln.strip().startswith("|")]
    if not lines:
        raise ValueError(f"{doc.doc_id}: khong tim thay bang Markdown trong than van ban")
    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    row_lines = lines[2:]
    sentences = []
    for row_line in row_lines:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        sentences.append(_row_to_sentence(header_cells, cells))

    table_md = "\n".join(lines)
    text = table_md + "\n\n" + "\n".join(sentences)
    breadcrumb = doc.title
    return [
        _build_chunk(
            doc,
            so_muc="1",
            parent_so_muc=None,
            breadcrumb=breadcrumb,
            text=text,
            doi_tuong="chung",
            loai_chunk="bang",
        )
    ]


def chunk_document(doc: Document, body_markdown: str) -> list[Chunk]:
    if doc.doc_type == "faq":
        return chunk_faq(doc, body_markdown)
    if doc.doc_type == "bao_hiem":
        return chunk_bao_hiem(doc, body_markdown)
    if doc.doc_type in ("dieu_khoan", "chinh_sach"):
        return chunk_dieu_khoan(doc, body_markdown)
    raise ValueError(f"{doc.doc_id}: doc_type '{doc.doc_type}' chua co quy tac chunk")
