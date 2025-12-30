# app.py
from __future__ import annotations
from typing import List, Dict
import argparse
from datetime import timedelta
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

    for org in targets:
        terms = ORG_SEARCH_TERMS.get(org, [])
        if not terms:
            continue

        # —— 可调直搜深度：完全由 config 控制
        raw_list = list(search_by_terms(
            terms,
            limit_pages=PER_ORG_SEARCH_LIMIT_PAGES,
            page_size=PER_ORG_SEARCH_PAGE_SIZE
        ))
        total_raw = len(raw_list)

        # 窗口过滤（保留 cs.*）
        after_window = [e for e in raw_list if is_cs(e) and in_time_window(e, start_utc, end_utc)]
        total_window = len(after_window)

        # 合并去重
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
    args = pa.parse_args()
    limit_files = max(0, int(args.limit_files))
    # 1) 时间窗口（昨天：北京时间）
    now = now_local()
    start_utc, end_utc = beijing_previous_day_window(now)
    _debug_print_window(now, start_utc, end_utc)

    # 2) 候选集 = 基线 +（按需）per-org 直搜补齐
    baseline_entries = _collect_baseline_entries(start_utc, end_utc)
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

    token_path = Path("config") / "mineru.txt"
    if not token_path.exists():
        print(f"缺少 MinerU token 文件：{token_path}")
        return
    token = token_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not token:
        print(f"MinerU token 文件为空：{token_path}")
        return

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
    )

    _argv = list(sys.argv)
    try:
        sys.argv = [sys.argv[0]]
        j2d.main()
        sys.argv = [sys.argv[0]]
        psel.main()
        sys.argv = [sys.argv[0]]
        psum.main()
    finally:
        sys.argv = _argv

if __name__ == "__main__":
    main()
