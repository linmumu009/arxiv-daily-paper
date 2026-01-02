from __future__ import annotations
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import List

def today_str() -> str:
    return datetime.now().date().isoformat()

def is_sep_line(s: str) -> bool:
    t = s.strip()
    return len(t) >= 10 and set(t) == {"#"}

def is_hyphen_sep(s: str) -> bool:
    t = s.strip()
    return len(t) >= 3 and set(t) == {"-"}

def normalize_meta_heading(s: str) -> str:
    t = s.strip()
    m = re.match(r"^📖\s*标题\s*[:：]\s*(.*)$", t)
    if m:
        return f"📖标题: {m.group(1).strip()}"
    m = re.match(r"^🌐\s*来源\s*[:：]\s*(.*)$", t)
    if m:
        return f"🌐来源: {m.group(1).strip()}"
    return s

def is_unwanted_meta(s: str) -> bool:
    t = s.strip()
    return t.startswith("👥") or t.startswith("📅")

def normalize_section_heading(s: str) -> str | None:
    t = s.strip()
    if re.match(r"^🛎️\s*文章简介\s*[:：]?$", t):
        return "🛎️文章简介"
    if re.match(r"^📝\s*重点思路\s*[:：]?$", t):
        return "📝重点思路"
    if re.match(r"^🔎\s*分析总结\s*[:：]?$", t):
        return "🔎分析总结"
    if re.match(r"^💡\s*个人观点\s*[:：]?$", t):
        return "💡个人观点"
    return None

def strip_md_marks(s: str) -> str:
    s2 = s.replace("**", "")
    ls = s2.lstrip()
    if ls.startswith("#"):
        s2 = ls.lstrip("#").lstrip()
    return s2

def split_blocks(lines: List[str]) -> List[List[str]]:
    blocks: List[List[str]] = []
    cur: List[str] = []
    for ln in lines:
        if is_sep_line(ln):
            if cur:
                blocks.append(cur)
                cur = []
            blocks.append([ln])
        else:
            cur.append(ln)
    if cur:
        blocks.append(cur)
    return blocks

def join_blocks(blocks: List[List[str]]) -> str:
    out: List[str] = []
    sep = "#" * 80
    for b in blocks:
        out.extend(b)
        out.append("")
        out.append("")
        out.append(sep)
        out.append("")
        out.append("")
    return "\n".join(out)

def clean_block(block: List[str]) -> List[str]:
    title_line = ""
    meta_title = ""
    meta_source = ""
    sections = {
        "🛎️文章简介": [],
        "📝重点思路": [],
        "🔎分析总结": [],
        "💡个人观点": [],
    }
    cur_sec = ""
    for s in block:
        if is_sep_line(s) or is_hyphen_sep(s):
            continue
        s2 = strip_md_marks(s)
        s2 = normalize_meta_heading(s2)
        if is_unwanted_meta(s2):
            continue
        h = normalize_section_heading(s2)
        if h is not None:
            cur_sec = h
            continue
        t = s2.strip()
        if not t:
            continue
        if t.startswith("📖标题:"):
            meta_title = t
            continue
        if t.startswith("🌐来源:"):
            meta_source = t
            continue
        if not title_line:
            title_line = t
            continue
        if cur_sec:
            sections[cur_sec].append(t)
    out: List[str] = []
    if title_line:
        out.append(title_line)
        out.append("")
    if meta_title:
        out.append(meta_title)
    if meta_source:
        out.append(meta_source)
    if meta_title or meta_source:
        out.append("")
    order = ["🛎️文章简介", "📝重点思路", "🔎分析总结", "💡个人观点"]
    for i, sec in enumerate(order):
        if sections[sec]:
            out.append(sec)
            for ln in sections[sec]:
                out.append(ln)
            if i < len(order) - 1:
                out.append("")
    return out

def clean_block_with_key(block: List[str]) -> tuple[List[str], tuple[str, str]]:
    title_line = ""
    meta_title = ""
    meta_source = ""
    sections = {
        "🛎️文章简介": [],
        "📝重点思路": [],
        "🔎分析总结": [],
        "💡个人观点": [],
    }
    cur_sec = ""
    for s in block:
        if is_sep_line(s) or is_hyphen_sep(s):
            continue
        s2 = strip_md_marks(s)
        s2 = normalize_meta_heading(s2)
        if is_unwanted_meta(s2):
            continue
        h = normalize_section_heading(s2)
        if h is not None:
            cur_sec = h
            continue
        t = s2.strip()
        if not t:
            continue
        if t.startswith("📖标题:"):
            meta_title = t
            continue
        if t.startswith("🌐来源:"):
            meta_source = t
            continue
        if not title_line:
            title_line = t
            continue
        if cur_sec:
            sections[cur_sec].append(t)
    out: List[str] = []
    if title_line:
        out.append(title_line)
        out.append("")
    if meta_title:
        out.append(meta_title)
    if meta_source:
        out.append(meta_source)
    if meta_title or meta_source:
        out.append("")
    order = ["🛎️文章简介", "📝重点思路", "🔎分析总结", "💡个人观点"]
    for i, sec in enumerate(order):
        if sections[sec]:
            out.append(sec)
            for ln in sections[sec]:
                out.append(ln)
            if i < len(order) - 1:
                out.append("")
    base = ""
    if meta_title:
        i = meta_title.find(":")
        base = meta_title[i + 1:].strip() if i != -1 else meta_title.strip()
    else:
        base = title_line.strip()
    first = ""
    for ch in base:
        if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            first = ch.lower()
            break
    if not first:
        first = (base[:1].lower() if base else "")
    return out, (first, base.lower())

def run_clean(file_path: Path) -> None:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    blocks = split_blocks(lines)
    items: List[tuple[tuple[str, str], List[str]]] = []
    for b in blocks:
        block_out, key = clean_block_with_key(b)
        if block_out:
            items.append((key, block_out))
    items.sort(key=lambda x: x[0])
    cleaned_blocks = [b for _, b in items]
    out_text = join_blocks(cleaned_blocks)
    out_text = re.sub(r"(📖标题:[^\n]*)\n+", r"\1\n", out_text)
    for sec in ("🛎️文章简介", "📝重点思路", "🔎分析总结", "💡个人观点"):
        out_text = re.sub(rf"({re.escape(sec)})\n+", r"\1\n", out_text)
    file_path.write_text(out_text, encoding="utf-8")

def run_rebuild(date_str: str, root: Path) -> Path:
    summary_dir = root / "summary" / date_str
    gather_dir = root / "summary_gather"
    gather_dir.mkdir(parents=True, exist_ok=True)
    out_path = gather_dir / f"{date_str}.txt"
    files = sorted(summary_dir.glob("*.txt"))
    out_lines: List[str] = []
    sep = "#" * 80
    items2: List[tuple[tuple[str, str], str, List[str]]] = []
    for p in files:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        lines = txt.splitlines()
        block_out, key = clean_block_with_key(lines)
        if block_out:
            items2.append((key, p.stem, block_out))
    items2.sort(key=lambda x: x[0])
    for i, (_, stem, block) in enumerate(items2):
        if i > 0:
            out_lines.append("")
            out_lines.append("")
        out_lines.append(sep)
        out_lines.append("")
        out_lines.append(f"{stem}.pdf")
        out_lines.append("")
        out_lines.append(sep)
        out_lines.append("")
        out_lines.extend(block)
    out_text = "\n".join(out_lines)
    out_text = re.sub(r"(📖标题:[^\n]*)\n+", r"\1\n", out_text)
    for sec in ("🛎️文章简介", "📝重点思路", "🔎分析总结", "💡个人观点"):
        out_text = re.sub(rf"({re.escape(sec)})\n+", r"\1\n", out_text)
    out_text = out_text.lstrip("\n")
    out_path.write_text(out_text, encoding="utf-8")
    return out_path

def main() -> None:
    pa = argparse.ArgumentParser("rewriteClean")
    pa.add_argument("--file", default="")
    pa.add_argument("--root", default=str(Path("SelectPaperRewrite")))
    pa.add_argument("--subdir", default="summary_gather")
    pa.add_argument("--date", default="")
    pa.add_argument("--rebuild", action="store_true")
    args = pa.parse_args()
    file_arg = args.file.strip()
    root = Path(args.root)
    if file_arg:
        fp = Path(file_arg)
    else:
        date_str = args.date.strip() or today_str()
        out = run_rebuild(date_str, root)
        print(str(out))
        return
    if not fp.exists():
        raise SystemExit(f"文件不存在：{fp}")
    run_clean(fp)
    print(str(fp))

if __name__ == "__main__":
    main()
