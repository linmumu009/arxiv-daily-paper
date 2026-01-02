from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List
from openai import AsyncOpenAI
import importlib.util

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def today_str() -> str:
    return datetime.now().date().isoformat()

def list_md_files(root: Path) -> List[Path]:
    return sorted(root.glob("*.md"))

def load_api_key() -> str:
    p = Path("config") / "gptgod.txt"
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise SystemExit(f"API Key 文件为空：{p}")
    return text

def make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=load_api_key(),
        base_url="https://gptgod.cloud/v1",
    )

def load_summary_example() -> str:
    p = Path("config") / "summary_prompt.py"
    if not p.exists():
        return ""
    spec = importlib.util.spec_from_file_location("summary_prompt", str(p))
    if not spec or not spec.loader:
        return ""
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "summary_example", "")

def build_sys_prompt() -> str:
    example = load_summary_example()
    return (
        "你是一个论文总结助手。参考示例的风格与结构，对给定的 Markdown 论文进行中文总结。"
        f"\n示例：\n{example}"
    )

def _is_sep_line(s: str) -> bool:
    t = s.strip()
    return len(t) >= 10 and set(t) == {"#"}

def _is_section_heading(s: str) -> bool:
    t = s.strip()
    if not t:
        return False
    heads = ("📖 标题", "🛎️ 文章简介", "📝 重点思路", "🔎 分析总结", "💡 个人观点")
    return any(t.startswith(h) for h in heads)

def sanitize_output(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i]
        s2 = s.replace("**", "")
        if not _is_sep_line(s2):
            ls = s2.lstrip()
            if ls.startswith("#"):
                s2 = ls.lstrip("#").lstrip()
        out.append(s2)
        if _is_section_heading(s2):
            out.append("")
        i += 1
    # 去除多余空行（最多保留一个）
    final: List[str] = []
    blank = False
    for s in out:
        if s.strip():
            final.append(s)
            blank = False
        else:
            if not blank:
                final.append("")
            blank = True
    return "\n".join(final).strip()

async def summarize_md(client: AsyncOpenAI, model: str, sys_prompt: str, md_text: str) -> str:
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": md_text},
        ],
        stream=False,
    )
    if resp.choices:
        msg = resp.choices[0].message
        return getattr(msg, "content", "") or ""
    return ""

async def process_one(p: Path, client: AsyncOpenAI, model: str, sys_prompt: str, out_summary_dir: Path, out_gather_path: Path, lock: asyncio.Lock, overwrite: bool) -> None:
    one_out = out_summary_dir / f"{p.stem}.txt"
    if one_out.exists() and not overwrite:
        return
    md_text = p.read_text(encoding="utf-8", errors="ignore")
    s = await summarize_md(client, model, sys_prompt, md_text)
    s2 = sanitize_output(s)
    one_out.write_text(s2, encoding="utf-8")
    async with lock:
        with out_gather_path.open("a", encoding="utf-8") as f:
            f.write(s2)
            f.write("\n\n############################################################\n\n\n")

async def run(date_str: str, md_root_base: Path, out_root: Path, model: str, concurrency: int, overwrite: bool) -> None:
    md_root = md_root_base / date_str
    if not md_root.exists():
        raise SystemExit(f"输入目录不存在：{md_root}")
    files = list_md_files(md_root)
    if not files:
        raise SystemExit(f"输入目录无 md 文件：{md_root}")
    client = make_client()
    sys_prompt = build_sys_prompt()
    out_summary_dir = ensure_dir(out_root / "summary" / date_str)
    out_gather_dir = ensure_dir(out_root / "summary_gather")
    out_gather_path = out_gather_dir / f"{date_str}.txt"
    if overwrite and out_gather_path.exists():
        out_gather_path.unlink(missing_ok=True)
    lock = asyncio.Lock()
    sem = asyncio.Semaphore(max(1, concurrency))
    total = len(files)
    done = 0
    print_lock = asyncio.Lock()
    async def _wrap(p: Path) -> None:
        nonlocal done
        async with sem:
            await process_one(p, client, model, sys_prompt, out_summary_dir, out_gather_path, lock, overwrite)
            async with print_lock:
                done += 1
                print(f"\r[rewrite] {done}/{total}", end="", flush=True)
    tasks = [asyncio.create_task(_wrap(p)) for p in files]
    await asyncio.gather(*tasks)
    print()
    print(str(out_summary_dir))
    print(str(out_gather_path))

def main() -> None:
    pa = argparse.ArgumentParser("selectPapers_rewrite")
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
    asyncio.run(run(date_str, md_root, out_root, args.model, max(1, args.concurrency), bool(args.overwrite)))

if __name__ == "__main__":
    main()
