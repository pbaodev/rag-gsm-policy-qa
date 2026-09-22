"""Ghep prompt cho Buoc 7 (da chot o docs/learning/07-*.md): K chunk da
sandwich-reorder, danh so [n] theo THU TU TRONG PROMPT (khong phai
chunk_id that) - he thong giu citation_map rieng (n -> chunk_id), LLM chi
can dem 1..K, giam rui ro bia chunk_id khong ton tai."""

from __future__ import annotations

from rag_gsm.schemas import Chunk

SYSTEM_PROMPT = (
    "Bạn là trợ lý tra cứu chính sách Green SM (dịch vụ gọi xe), luôn trả lời bằng tiếng Việt. "
    "Chỉ được dùng thông tin trong các khối ngữ cảnh được cung cấp bên dưới, không dùng kiến thức "
    "ngoài. Sau mỗi khẳng định lấy từ nguồn, chèn ngay số thứ tự khối tương ứng trong dấu ngoặc "
    "vuông, ví dụ [1] hoặc [2]. Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ là không có đủ thông "
    "tin thay vì đoán."
)

KHONG_BIET_TEXT = (
    "Xin lỗi, hiện chúng tôi chưa có đủ thông tin trong chính sách để trả lời chính xác câu hỏi "
    "này. Bạn vui lòng liên hệ Hotline 1555 hoặc email support.vn@greensm.com để được hỗ trợ "
    "trực tiếp."
)


def build_prompt(query: str, chunks: list[Chunk]) -> tuple[str, str, dict[int, str]]:
    citation_map = {i + 1: c.chunk_id for i, c in enumerate(chunks)}
    blocks = "\n\n".join(f"[{i + 1}] ({c.heading_path})\n{c.text}" for i, c in enumerate(chunks))
    user = f"Ngữ cảnh:\n{blocks}\n\nCâu hỏi: {query}"
    return SYSTEM_PROMPT, user, citation_map
