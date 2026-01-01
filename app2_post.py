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

def find_copy_files(gather_root: Path, date_str: str) -> list[Path]:
    date_dir = gather_root / date_str
    if date_dir.exists():
        return [p for p in sorted(date_dir.glob("*")) if "copy" in p.name.lower()]
    return [p for p in sorted(gather_root.glob(f"*{date_str}*")) if "copy" in p.name.lower()]

def find_summary_matches(summary_dir: Path, selected_blocks: list[str]) -> list[Path]:
    selected_set = {b.strip() for b in selected_blocks}
    out = []
    for p in sorted(summary_dir.glob("*.txt")):
        txt = read_text(p).strip()
        if txt in selected_set:
            out.append(p)
    return out

def move_pdfs(pdf_dir: Path, dest_dir: Path, stems: list[str]) -> int:
    ensure_dir(dest_dir)
    moved = 0
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
    return moved

def main():
    pa = argparse.ArgumentParser("app2_post")
    pa.add_argument("--date", default="")
    pa.add_argument("--gather-root", default=str(Path("dataSelect") / "summary_gather"))
    pa.add_argument("--summary-root", default=str(Path("dataSelect") / "summary"))
    pa.add_argument("--pdf-root", default=str(Path("dataSelect") / "pdf"))
    pa.add_argument("--out-root", default=str(Path("dataSelect") / "selectPDF"))
    args = pa.parse_args()

    date_str = args.date.strip() or datetime.now().date().isoformat()
    gather_root = Path(args.gather_root)
    summary_dir = Path(args.summary_root) / date_str
    pdf_dir = Path(args.pdf_root) / date_str
    dest_dir = Path(args.out_root) / date_str

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

    blocks = []
    for cp in copies:
        blocks.extend(split_blocks(read_text(cp)))
    if not blocks:
        print("copy 文件中无可用于匹配的内容")
        return

    matched = find_summary_matches(summary_dir, blocks)
    stems = [p.stem for p in matched]
    moved = move_pdfs(pdf_dir, dest_dir, stems)
    print(f"选中 {len(stems)} 篇，移动 PDF {moved} 个 -> {dest_dir}")

if __name__ == "__main__":
    main()
