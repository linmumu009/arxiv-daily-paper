from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple
from config import LOCAL_TZ, ARXIV_CATEGORIES

def beijing_previous_day_window(now_local):
    """
    原逻辑是北京时间昨天 00:00–24:00 → UTC 16:00–次日15:59。
    但 arXiv 发布在 UTC 20:00 → 北京次日04:00。
    因此这里延后 8 小时，让窗口覆盖完整批次。
    """
    now_local = now_local.replace(tzinfo=None)
    today = now_local.date()
    yesterday = today - timedelta(days=1)
    # 原版是 00:00–24:00，现在延后 8 小时
    start_beijing = datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=8)
    end_beijing = start_beijing + timedelta(days=1) - timedelta(microseconds=1)
    start_utc = start_beijing - timedelta(hours=8)
    end_utc = end_beijing - timedelta(hours=8)
    return start_utc.replace(tzinfo=timezone.utc), end_utc.replace(tzinfo=timezone.utc)

def in_time_window(entry: Dict[str, Any], start_utc: datetime, end_utc: datetime) -> bool:
    dt = entry.get("updated") or entry.get("published")
    return bool(dt and start_utc <= dt <= end_utc)

def is_cs(entry: Dict[str, Any]) -> bool:
    cat = entry.get("primary_category") or ""
    return any(cat.startswith(p) for p in ARXIV_CATEGORIES)

import re
from config import TOPIC_INCLUDE_PATTERNS, TOPIC_EXCLUDE_PATTERNS

_INC = [re.compile(p, re.IGNORECASE) for p in TOPIC_INCLUDE_PATTERNS]
_EXC = [re.compile(p, re.IGNORECASE) for p in (TOPIC_EXCLUDE_PATTERNS or [])]

def is_target_topic(entry: Dict[str, Any]) -> bool:
    hay = "\n".join([
        entry.get("title",""),
        entry.get("summary",""),
        entry.get("comment",""),
        entry.get("journal_ref",""),
    ])
    if any(p.search(hay) for p in _EXC):
        return False
    return any(p.search(hay) for p in _INC)
