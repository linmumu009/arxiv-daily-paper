from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
from selectPapers_rewrite import run as rewrite_run
from rewriteClean import run_rebuild

def today_str() -> str:
    return datetime.now().date().isoformat()

def main() -> None:
    pa = argparse.ArgumentParser("app2_post_later")
    pa.add_argument("--date", default="")
    pa.add_argument("--md-root", default=str(Path("selectPapers") / "md"))
    pa.add_argument("--out-root", default=str(Path("SelectPaperRewrite")))
    pa.add_argument("--model", default="claude-sonnet-4-5-all")
    pa.add_argument("--concurrency", type=int, default=8)
    pa.add_argument("--overwrite", action="store_true")
    args = pa.parse_args()
    date_str = args.date.strip() or today_str()
    md_root = Path(args.md_root)
    out_root = Path(args.out_root)
    asyncio.run(rewrite_run(date_str, md_root, out_root, args.model, max(1, args.concurrency), bool(args.overwrite)))
    out_path = run_rebuild(date_str, out_root)
    print(str(out_path))

if __name__ == "__main__":
    main()
