from __future__ import annotations
import os, re
from pathlib import Path
import fitz

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._/-]+")

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)

def split_first_pages(src_pdf: str, out_dir: str, pages: int = 2) -> str:
    ensure_dir(out_dir)
    doc = fitz.open(src_pdf)
    k = max(1, pages)
    k = min(k, len(doc))
    new = fitz.open()
    new.insert_pdf(doc, from_page=0, to_page=k-1)
    base = os.path.basename(src_pdf)
    rel = SAFE_NAME.sub("_", base)
    name, ext = os.path.splitext(rel)
    dst = os.path.join(out_dir, f"{name}.p{k}.pdf") if k > 1 else os.path.join(out_dir, f"{name}.p1.pdf")
    new.save(dst)
    new.close()
    doc.close()
    return dst

def split_dir(src_dir: str, out_dir: str, pages: int = 2) -> list[str]:
    ensure_dir(out_dir)
    out: list[str] = []
    for entry in Path(src_dir).glob("*.pdf"):
        try:
            dst = split_first_pages(str(entry), out_dir, pages=pages)
            out.append(dst)
        except Exception:
            pass
    return out
