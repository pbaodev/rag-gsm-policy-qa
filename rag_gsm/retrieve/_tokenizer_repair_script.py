"""Chay bang MOT MOI TRUONG RIENG qua `uv run --with "transformers<5" --with
protobuf python _tokenizer_repair_script.py <model_name> <out_dir>` - xem
loi that va ly do o rerank.py. Khong import gi tu rag_gsm: script nay
chay ngoai venv chinh cua du an, tam thoi, chi de tao lai tokenizer.json.
"""

from __future__ import annotations

import sys

from transformers import AutoTokenizer


def main() -> None:
    model_name, out_dir = sys.argv[1], sys.argv[2]
    tok = AutoTokenizer.from_pretrained(model_name)
    tok.save_pretrained(out_dir)
    print(f"Da luu tokenizer da sua vao {out_dir}")


if __name__ == "__main__":
    main()
