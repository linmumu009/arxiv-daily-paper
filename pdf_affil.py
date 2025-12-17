# pdf_affil.py
from __future__ import annotations
from typing import Optional, List
import re
import fitz
from config import AFFIL_HINT_KEYWORDS

def extract_affiliation_text(pdf_path: str, max_pages: int = 2) -> str:
    doc = fitz.open(pdf_path)
    out_lines: List[str] = []
    n = min(len(doc), max_pages if max_pages > 0 else 1)
    for i in range(n):
        page = doc.load_page(i)
        h = page.rect.height
        try:
            d = page.get_text("dict")
            blocks = d.get("blocks", [])
            cand_top: List[str] = []
            cand_foot: List[str] = []
            for b in blocks:
                for l in b.get("lines", []):
                    spans = l.get("spans", [])
                    s = "".join(sp.get("text", "") for sp in spans).strip()
                    bbox = l.get("bbox", [0, 0, 0, 0])
                    y0 = bbox[1] if isinstance(bbox, (list, tuple)) and len(bbox) >= 2 else 0
                    if not s:
                        continue
                    ns = _normalize_line(s)
                    if _is_noise(ns):
                        continue
                    if y0 <= h * 0.35:
                        if _looks_affil(ns):
                            cand_top.append(ns)
                    elif y0 >= h * 0.6:
                        if _looks_affil(ns):
                            cand_foot.append(ns)
            lines = cand_top + cand_foot
            if not lines:
                raw = page.get_text("text") or ""
                for ln in raw.splitlines():
                    ns = _normalize_line(ln)
                    if not ns or _is_noise(ns):
                        continue
                    if _looks_affil(ns):
                        out_lines.append(ns)
            else:
                out_lines.extend(lines)
        except Exception:
            raw = page.get_text("text") or ""
            for ln in raw.splitlines():
                ns = _normalize_line(ln)
                if not ns or _is_noise(ns):
                    continue
                if _looks_affil(ns):
                    out_lines.append(ns)
    doc.close()
    uniq = []
    seen = set()
    for s in out_lines:
        if s not in seen:
            uniq.append(s)
            seen.add(s)
    return "\n".join(uniq).strip()

def _normalize_line(s: str) -> str:
    s = s.replace("•", " ").replace("·", " ").replace("–", "-").replace("—", "-")
    s = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _is_noise(s: str) -> bool:
    if not s:
        return True
    zl = s.lower()
    if zl.startswith("abstract") or zl.startswith("introduction"):
        return True
    if "arxiv" in zl or "preprint" in zl:
        return True
    if "license" in zl or "copyright" in zl:
        return True
    if "http://" in zl or "https://" in zl or "doi" in zl:
        return True
    if "corresponding author" in zl:
        return True
    if "@gmail" in zl or "@outlook" in zl or "@qq.com" in zl or "@me.com" in zl:
        return True
    if "acknowledgement" in zl or "acknowledgment" in zl:
        return True
    if "available on huggingface" in zl or "hosted on huggingface" in zl:
        return True
    if re.search(r"\bon\s+hugging\s*face\b", zl) and not re.search(r"\binc\b|\bresearch\b", zl):
        return True
    return False

def _looks_affil(s: str) -> bool:
    for k in AFFIL_HINT_KEYWORDS:
        if k.lower() in s.lower():
            return True
    if re.search(r"\b(University|Institute|Laboratory|Lab|Department|Dept|College|School|Center|Centre)\b", s, re.IGNORECASE):
        return True
    if re.search(r"^\d+\s", s):
        return True
    if re.search(r"\bInc\.|\bLLC\b|\bLtd\.\b|\bGmbH\b|\bS\.A\.\b", s):
        return True
    return False
