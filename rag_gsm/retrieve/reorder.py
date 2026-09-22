"""Context reorder "sandwich" (Buoc 7, nhung nam o retrieve/ theo
kien-truc-code.md): giam hieu ung lost-in-the-middle (Liu et al. 2023)
bang cach dat hang tot nhat o hai dau, hang kem nhat o giua. Thuan tuy
sap xep - khong dung LangChain (Buoc 0.3), khong can LLM."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def sandwich_reorder(ranked: list[T]) -> list[T]:
    """Dau vao da xep hang TOT -> KEM. Hang le (1,3,5,...) tu dau vao
    giua; hang chan (2,4,...) tu cuoi lui vao giua.
    Vi du [A(1),B(2),C(3)] -> [A,C,B] (A dau, B cuoi, C kem nhat o giua)."""
    odd = ranked[0::2]
    even = ranked[1::2]
    return odd + list(reversed(even))
