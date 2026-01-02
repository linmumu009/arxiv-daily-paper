from __future__ import annotations
import argparse
from pathlib import Path
import shutil
from datetime import datetime

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def split_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks = []
    buf = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("#") and len(s) >= 10 and set(s) == {"#"}:
            if buf:
                blocks.append("\n".join(buf).strip())
                buf = []
        else:
            buf.append(ln)
    if buf:
        blocks.append("\n".join(buf).strip())
    return [b for b in blocks if b]

def _is_pdf_name_line(ln: str) -> bool:
    s = ln.strip()
    if not s:
        return False
    if s.startswith("#"):
        s = s.lstrip("#").strip()
    return s.lower().endswith(".pdf")

def normalize_block(block: str) -> str:
    lines = block.splitlines()
    i = 0
    n = len(lines)
    while i < n and _is_pdf_name_line(lines[i]):
        i += 1
    return "\n".join(lines[i:]).strip()

def find_copy_files(gather_root: Path, date_str: str) -> list[Path]:
    date_dir = gather_root / date_str
    if date_dir.exists():
        return [p for p in sorted(date_dir.glob("*")) if "copy" in p.name.lower()]
    return [p for p in sorted(gather_root.glob(f"*{date_str}*")) if "copy" in p.name.lower()]

def find_summary_matches(summary_dir: Path, selected_blocks: list[str]) -> list[tuple[Path, str]]:
    selected_set = {normalize_block(b) for b in selected_blocks}
    out: list[tuple[Path, str]] = []
    for p in sorted(summary_dir.glob("*.txt")):
        txt = read_text(p).strip()
        if txt in selected_set:
            out.append((p, txt))
    return out

def move_pdfs(pdf_dir: Path, dest_dir: Path, stems: list[str]) -> tuple[int, list[str]]:
    ensure_dir(dest_dir)
    moved = 0
    moved_stems: list[str] = []
    for stem in stems:
        cand = pdf_dir / f"{stem}.pdf"
        src = cand if cand.exists() else None
        if not src:
            found = list(pdf_dir.rglob(f"{stem}.pdf"))
            if found:
                src = found[0]
        if not src:
            continue
        dst = dest_dir / src.name
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))
        moved += 1
        moved_stems.append(stem)
    return moved, moved_stems

def annotate_copy_file(cp: Path, block_to_stems: dict[str, list[str]]) -> None:
    blocks = split_blocks(read_text(cp))
    lines: list[str] = []
    sep = "############################################################"
    for b in blocks:
        clean = normalize_block(b)
        stems = block_to_stems.get(clean.strip(), [])
        for s in stems:
            lines.append(f"{s}.pdf")
            lines.append("")
            lines.append("")
            lines.append(sep)
            lines.append("")
            lines.append("")
        lines.append(clean)
        lines.append("")
        lines.append("")
        lines.append(sep)
        lines.append("")
        lines.append("")
    text = "\n".join(lines) + "\n"
    cp.write_text(text, encoding="utf-8")

def main():
    pa = argparse.ArgumentParser("app2_post")
    pa.add_argument("--date", default="")
    pa.add_argument("--gather-root", default=str(Path("dataSelect") / "summary_gather"))
    pa.add_argument("--summary-root", default=str(Path("dataSelect") / "summary"))
    pa.add_argument("--pdf-root", default=str(Path("dataSelect") / "pdf"))
    pa.add_argument("--md-root", default=str(Path("dataSelect") / "md"))
    pa.add_argument("--out-root", default=str(Path("selectPapers") / "PDF"))
    pa.add_argument("--out-md-root", default=str(Path("selectPapers") / "md"))
    args = pa.parse_args()

    date_str = args.date.strip() or datetime.now().date().isoformat()
    gather_root = Path(args.gather_root)
    summary_dir = Path(args.summary_root) / date_str
    pdf_dir = Path(args.pdf_root) / date_str
    md_dir = Path(args.md_root) / date_str
    dest_dir = Path(args.out_root) / date_str
    dest_md_dir = Path(args.out_md_root) / date_str

    copies = find_copy_files(gather_root, date_str)
    if not copies:
        print(f"未找到 copy 文件：{gather_root}/{date_str}")
        return
    if not summary_dir.exists():
        print(f"未找到摘要目录：{summary_dir}")
        return
    if not pdf_dir.exists():
        print(f"未找到 PDF 目录：{pdf_dir}")
        return
    if not md_dir.exists():
        print(f"未找到 MD 目录：{md_dir}")

    blocks: list[str] = []
    for cp in copies:
        blocks.extend(split_blocks(read_text(cp)))
    if not blocks:
        print("copy 文件中无可用于匹配的内容")
        return

    matched = find_summary_matches(summary_dir, blocks)
    stems = [p.stem for p, _ in matched]
    moved_count, moved_stems = move_pdfs(pdf_dir, dest_dir, stems)
    def move_mds(md_dir: Path, dest_dir: Path, stems: list[str]) -> tuple[int, list[str]]:
        ensure_dir(dest_dir)
        moved = 0
        moved_stems: list[str] = []
        for stem in stems:
            cand = md_dir / f"{stem}.md"
            src = cand if cand.exists() else None
            if not src:
                found = list(md_dir.rglob(f"{stem}.md"))
                if found:
                    src = found[0]
            if not src:
                continue
            dst = dest_dir / src.name
            if dst.exists():
                continue
            shutil.move(str(src), str(dst))
            moved += 1
            moved_stems.append(stem)
        return moved, moved_stems
    moved_md, moved_md_stems = move_mds(md_dir, dest_md_dir, stems)
    block_to_stems: dict[str, list[str]] = {}
    for p, txt in matched:
        key = txt.strip()
        block_to_stems.setdefault(key, []).append(p.stem)
    for cp in copies:
        annotate_copy_file(cp, block_to_stems)
    print(f"选中 {len(stems)} 篇，移动 PDF {moved_count} 个 -> {dest_dir}")
    print(f"移动 MD {moved_md} 个 -> {dest_md_dir}")

if __name__ == "__main__":
    main()
