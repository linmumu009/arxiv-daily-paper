from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, List


def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json_any(path: Path) -> List[Any]:
    try:
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            return [obj]
    except Exception:
        pass
    items: List[Any] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    items.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        return []
    return items


def main() -> None:
    pa = argparse.ArgumentParser("pdfSelect")
    pa.add_argument("--input", default="")
    pa.add_argument("--out-root", default=str(Path("dataSelect")))
    args = pa.parse_args()

    if args.input.strip():
        in_path = Path(args.input.strip())
    else:
        today = datetime.now().date().isoformat()
        in_path = Path("data_output") / "decide" / f"{today}.json"
    if not in_path.exists():
        raise SystemExit(f"输入文件不存在：{in_path}")

    date_str = in_path.stem
    src_md_dir = Path("data") / "md" / date_str
    src_pdf_dir = Path("cache_pdfs")
    dst_md_dir = ensure_dir(Path(args.out_root) / "md" / date_str)
    dst_pdf_dir = ensure_dir(Path(args.out_root) / "pdf" / date_str)

    data = read_json_any(in_path)
    stems: List[str] = []
    for it in data:
        if not isinstance(it, dict):
            continue
        if bool(it.get("is_large", False)):
            fn = str(it.get("文件名") or "").strip()
            if not fn:
                continue
            stem = Path(fn).stem
            if stem:
                stems.append(stem)

    copied_md = 0
    copied_pdf = 0
    for stem in stems:
        src_pdf = src_pdf_dir / f"{stem}.pdf"
        if not src_pdf.exists():
            found = list(src_pdf_dir.rglob(f"{stem}.pdf"))
            if found:
                src_pdf = found[0]
        if src_pdf.exists():
            dst_pdf = dst_pdf_dir / src_pdf.name
            if not dst_pdf.exists():
                shutil.copy2(src_pdf, dst_pdf)
            copied_pdf += 1
        src_md = src_md_dir / f"{stem}.md"
        if src_md.exists():
            dst_md = dst_md_dir / src_md.name
            if not dst_md.exists():
                shutil.copy2(src_md, dst_md)
            copied_md += 1

    print(f"pdf: {copied_pdf} -> {dst_pdf_dir}")
    print(f"md: {copied_md} -> {dst_md_dir}")


if __name__ == "__main__":
    main()
