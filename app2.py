# app.py
from __future__ import annotations
from typing import List, Dict
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import (
    DRY_RUN, DEBUG, CLASSIFY_FROM_PDF, ENABLE_TOPIC_FILTER,
    ORG_SEARCH_TERMS,
    PER_ORG_SEARCH_LIMIT_PAGES, PER_ORG_SEARCH_PAGE_SIZE,
    PDF_CACHE_DIR,
)
from fetch_arxiv import iter_recent_cs, search_by_terms, get_arxiv_id
from filters import beijing_previous_day_window, in_time_window, is_cs, is_target_topic
from classify import group_by_org
from prefetch import cache_pdfs
from utils import now_local
from pdf2md import run_local_batch
import json2decide as j2d
import pdfSelect as psel
import pdfSummary as psum
import sys

# 行为开关
FILL_MISSING_BY_ORG = True       # 仅对“基线为空”的机构直搜补齐（更快）
ALWAYS_PER_ORG_SEARCH = False    # True=所有机构都跑直搜（更全但更慢）

def _debug_print_window(now, start_utc, end_utc):
    if not DEBUG:
        return
    print(f"[DEBUG] now local = {now.isoformat()}")
    print(f"[DEBUG] window (UTC) = {start_utc.isoformat()}  ->  {end_utc.isoformat()}")

def _collect_baseline_entries(start_utc, end_utc) -> List[Dict]:
    """
    基线：遍历 cs.* 多页（由 fetch_arxiv 按 config 控制分页），再按时间窗口过滤。
    新增：传入 start_utc，让 iter_recent_cs 能在遇到旧论文时提前中断。
    """
    entries: List[Dict] = []
    total_scanned = 0
    for e in iter_recent_cs(start_utc=start_utc):   # ✅ 这里传入 start_utc
        total_scanned += 1
        if is_cs(e) and in_time_window(e, start_utc, end_utc):
            entries.append(e)
    if DEBUG:
        print(f"[DEBUG] scanned={total_scanned}  baseline_matches={len(entries)}")
    return entries


def build_candidates_with_fallback(baseline_entries: List[Dict], start_utc, end_utc) -> List[Dict]:
    """
    1) 用摘要/标题对 baseline 做粗分（只为确定需要直搜的机构，不用于最终分类）。
    2) 对选定机构逐个执行 per-org 直搜（可配置深度），合并去重，返回候选列表。
       —— 诊断日志：raw（直搜返回总数）、in_window（落在窗口的）、added（真正新增）。
    """
    rough = group_by_org(baseline_entries)
    if DEBUG:
        print(f"[DEBUG] baseline org-buckets(rough): { {k: len(v) for k, v in rough.items()} }")

    if ALWAYS_PER_ORG_SEARCH:
        targets = list(ORG_SEARCH_TERMS.keys())
    elif FILL_MISSING_BY_ORG:
        targets = [org for org in ORG_SEARCH_TERMS.keys() if not rough.get(org)]
    else:
        targets = [] if rough else list(ORG_SEARCH_TERMS.keys())

    if DEBUG:
        print(f"[DEBUG] per-org search targets: {targets}")

    merged = list(baseline_entries)
    seen_ids = { (e.get("id") or "") for e in merged }

    def _job(org: str):
        terms = ORG_SEARCH_TERMS.get(org, [])
        if not terms:
            return org, []
        raw_list = list(search_by_terms(
            terms,
            limit_pages=PER_ORG_SEARCH_LIMIT_PAGES,
            page_size=PER_ORG_SEARCH_PAGE_SIZE
        ))
        return org, raw_list

    org_search_concurrency = getattr(build_candidates_with_fallback, "_org_search_concurrency", 1)
    with ThreadPoolExecutor(max_workers=max(1, int(org_search_concurrency))) as ex:
        futures = { ex.submit(_job, org): org for org in targets }
        for fut in as_completed(futures):
            org, raw_list = fut.result()
            total_raw = len(raw_list)
            after_window = [e for e in raw_list if is_cs(e) and in_time_window(e, start_utc, end_utc)]
            total_window = len(after_window)
            before = len(merged)
            for e in after_window:
                xid = e.get("id") or ""
                if xid not in seen_ids:
                    merged.append(e)
                    seen_ids.add(xid)
            added = len(merged) - before
            if DEBUG:
                print(f"[FALLBACK-DEBUG] {org}: raw={total_raw}, in_window={total_window}, added={added}, merged total now {len(merged)}")

    return merged

def main():
    pa = argparse.ArgumentParser("app2")
    pa.add_argument("--limit-files", type=int, default=0)
    pa.add_argument("--decide-concurrency", type=int, default=10)
    pa.add_argument("--org-search-concurrency", type=int, default=6)
    pa.add_argument("--window-hours", type=int, default=0)
    pa.add_argument("--configdepositary", choices=["A", "B"], default="B")
    args = pa.parse_args()
    limit_files = max(0, int(args.limit_files))
    decide_concurrency = max(1, int(args.decide_concurrency))
    org_search_concurrency = max(1, int(args.org_search_concurrency))
    window_hours = max(0, int(args.window_hours))
    # 1) 时间窗口（昨天：北京时间）
    now = now_local()
    if window_hours > 0:
        end_utc = datetime.now(timezone.utc)
        start_utc = end_utc - timedelta(hours=window_hours)
    else:
        start_utc, end_utc = beijing_previous_day_window(now)
    _debug_print_window(now, start_utc, end_utc)

    # 2) 候选集 = 基线 +（按需）per-org 直搜补齐
    baseline_entries = _collect_baseline_entries(start_utc, end_utc)
    build_candidates_with_fallback._org_search_concurrency = org_search_concurrency
    candidates = build_candidates_with_fallback(baseline_entries, start_utc, end_utc)
    

    if ENABLE_TOPIC_FILTER:
        before = len(candidates)
        candidates = [e for e in candidates if is_target_topic(e)]
        if DEBUG:
            print(f"[DEBUG] topic filter: {before} -> {len(candidates)}")

    if DEBUG:
        print(f"[DEBUG] candidates after fallback merge: {len(candidates)}")

    if not candidates:
        print("昨天窗口内没有候选论文（基线 + 直搜均为空）。")
        return
    # 3) 缓存 PDF 到 cache_pdfs/当日日期
    run_date = now.date().isoformat()
    id2pdf = cache_pdfs(candidates, subdir=run_date)

    cache_root = Path(PDF_CACHE_DIR) / run_date
    pdfs = sorted(cache_root.rglob("*.pdf"))
    if limit_files:
        pdfs = pdfs[:limit_files]
    if DEBUG:
        print(f"[DEBUG] cached pdfs in {cache_root}: {len(pdfs)}")
    if not pdfs:
        print(f"未发现缓存 PDF：{cache_root}")
        return

    if args.configdepositary == "B":
        import importlib.util
        dep_path = Path("config") / "configDepositary.py"
        if not dep_path.exists():
            print(f"缺少配置文件：{dep_path}")
            return
        spec = importlib.util.spec_from_file_location("configDepositary", str(dep_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        token = getattr(mod, "minerU_Token", "")
        if not token:
            print("配置文件中的 MinerU_Token 为空")
            return
    else:
        token_path = Path("config") / "mineru.txt"
        if not token_path.exists():
            print(f"缺少 MinerU token 文件：{token_path}")
            return
        token = token_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not token:
            print(f"MinerU token 文件为空：{token_path}")
            return

    out_decide_dir = Path("data_output") / "decide"
    out_decide_dir.mkdir(parents=True, exist_ok=True)
    out_decide_path = out_decide_dir / f"{run_date}.json"
    if args.configdepositary == "B":
        import importlib.util
        dep_path2 = Path("config") / "configDepositary.py"
        spec2 = importlib.util.spec_from_file_location("configDepositary", str(dep_path2))
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)
        api_key = getattr(mod2, "qwen_api_key", "")
        sum_system_prompt = getattr(mod2, "system_prompt", "")
        sum_user_prompt = getattr(mod2, "user_prompt", "")
        org_sys_prompt = getattr(mod2, "org_system_prompt", "")
    else:
        api_key_path = Path("config") / "qwen_api.txt"
        api_key = api_key_path.read_text(encoding="utf-8", errors="ignore").strip() if api_key_path.exists() else ""
        sum_system_prompt = ""
        sum_user_prompt = ""
        org_sys_prompt = ""
    base_url_llm = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_llm = "qwen-plus"
    lock = threading.Lock()
    sum_lock = threading.Lock()
    out_summary_dir = Path("dataSelect") / "summary" / run_date
    out_summary_dir.mkdir(parents=True, exist_ok=True)
    out_gather_dir = Path("dataSelect") / "summary_gather" / run_date
    out_gather_dir.mkdir(parents=True, exist_ok=True)
    out_gather_path = out_gather_dir / f"{run_date}.txt"
    futures = []
    def on_json(path: Path) -> None:
        def job(pth: Path) -> None:
            text = j2d.load_first_pages_text(pth, max_page_idx=2)
            item = j2d.call_qwen_plus(api_key, base_url_llm, model_llm, text, file_name=pth.name, sys_prompt=org_sys_prompt or None)
            with lock:
                j2d.append_result(out_decide_path, item)
            try:
                if bool(item.get("is_large", False)):
                    fn = str(item.get("文件名") or "").strip()
                    stem = Path(fn).stem
                    if stem:
                        src_md = (Path("data") / "md" / run_date / f"{stem}.md")
                        dst_md_dir = Path("dataSelect") / "md" / run_date
                        dst_pdf_dir = Path("dataSelect") / "pdf" / run_date
                        dst_md_dir.mkdir(parents=True, exist_ok=True)
                        dst_pdf_dir.mkdir(parents=True, exist_ok=True)
                        src_pdf = (Path(PDF_CACHE_DIR) / run_date / f"{stem}.pdf")
                        if not src_pdf.exists():
                            found = list((Path(PDF_CACHE_DIR) / run_date).rglob(f"{stem}.pdf"))
                            if found:
                                src_pdf = found[0]
                        if src_pdf.exists():
                            dst_pdf = dst_pdf_dir / src_pdf.name
                            if not dst_pdf.exists():
                                import shutil
                                shutil.copy2(src_pdf, dst_pdf)
                        if src_md.exists():
                            dst_md = dst_md_dir / src_md.name
                            if not dst_md.exists():
                                import shutil
                                shutil.copy2(src_md, dst_md)
                            one_out = out_summary_dir / f"{stem}.txt"
                            if not one_out.exists():
                                md_text = dst_md.read_text(encoding="utf-8", errors="ignore")
                                sum_client = psum.make_client(api_key=api_key, base_url=base_url_llm)
                                summary = psum.summarize_md(sum_client, "qwen2.5-72b-instruct", md_text, file_name=dst_md.name, system_prompt=sum_system_prompt or None, user_prompt_prefix=sum_user_prompt or None)
                                one_out.write_text(summary, encoding="utf-8")
                                with sum_lock:
                                    with out_gather_path.open("a", encoding="utf-8") as f:
                                        f.write(summary)
                                        f.write("\n\n\n############################################################\n\n\n")
            except Exception:
                pass
        futures.append(ex.submit(job, path))
    ex = ThreadPoolExecutor(max_workers=decide_concurrency)
    try:
        run_local_batch(
            pdfs=pdfs,
            out_md_root=Path("data") / "md",
            out_json_root=Path("data") / "json",
            base_url="https://mineru.net",
            token=token,
            model_version="vlm",
            timeout_sec=900,
            poll_sec=3,
            upload_retries=6,
            keep_zip=False,
            is_ocr=False,
            enable_formula=True,
            enable_table=True,
            language="ch",
            extra_formats=[],
            page_ranges=None,
            batch_size=10,
            upload_concurrency=10,
            limit_files=limit_files,
            on_json=on_json,
        )
    finally:
        for f in futures:
            try:
                f.result()
            except Exception:
                pass
        ex.shutdown(wait=True)

    _argv = list(sys.argv)
    try:
        sys.argv = [sys.argv[0]]
        print(str(out_decide_path))
        sys.argv = [sys.argv[0]]
        psel.main()
        sys.argv = [sys.argv[0]]
        psum.main()
    finally:
        sys.argv = _argv
    try:
        import shutil
        copy_path = out_gather_dir / f"{run_date} copy.txt"
        shutil.copy2(out_gather_path, copy_path)
        print(str(copy_path))
    except Exception:
        pass

if __name__ == "__main__":
    main()
