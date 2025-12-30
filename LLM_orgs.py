from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import List
from openai import OpenAI
from utils import now_local
from config import INSTITUTIONS_PATTERNS, USE_HARDLINKS

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)

def canonical_orgs() -> List[str]:
    return list(INSTITUTIONS_PATTERNS.keys())

def normalize_org(name: str) -> str | None:
    n = (name or "").strip()
    if not n:
        return None
    m = n.lower()
    mapping = {
        "meta": "Meta", "meta ai": "Meta", "fair": "Meta", "facebook ai research": "Meta",
        "google": "Google", "google research": "Google", "google deepmind": "Google", "deepmind": "Google",
        "microsoft": "Microsoft", "microsoft research": "Microsoft", "msr": "Microsoft", "msra": "Microsoft",
        "ibm": "IBM", "ibm research": "IBM",
        "amazon": "Amazon", "aws": "Amazon", "amazon ai": "Amazon", "aws ai": "Amazon",
        "apple": "Apple",
        "anthropic": "Anthropic",
        "nvidia": "NVIDIA",
        "hugging face": "HuggingFace", "huggingface": "HuggingFace",
        "laion": "LAION",
        "eleuther ai": "EleutherAI", "eleutherai": "EleutherAI",
        "ai2": "AI2", "allen institute for ai": "AI2", "allen institute": "AI2", "allen ai": "AI2",
        "mit": "MIT", "massachusetts institute of technology": "MIT", "csail": "MIT",
        "stanford": "Stanford", "stanford university": "Stanford",
        "cmu": "CMU", "carnegie mellon": "CMU", "carnegie mellon university": "CMU",
        "uc berkeley": "Berkeley", "university of california, berkeley": "Berkeley", "berkeley": "Berkeley",
        "tsinghua": "Tsinghua", "tsinghua university": "Tsinghua", "清华": "Tsinghua",
        "pku": "PekingU", "peking university": "PekingU", "北京大学": "PekingU",
        "oxford": "Oxford", "university of oxford": "Oxford",
        "cambridge": "Cambridge", "university of cambridge": "Cambridge",
        "eth": "ETH", "eth zurich": "ETH", "eth zürich": "ETH",
        "huawei": "Huawei", "noah's ark lab": "Huawei", "诺亚方舟": "Huawei", "华为": "Huawei",
        "baidu": "Baidu", "百度": "Baidu",
        "sensetime": "SenseTime", "商汤": "SenseTime",
        "megvii": "Megvii", "旷视": "Megvii",
        "yitu": "Yitu", "依图": "Yitu",
        "tencent": "Tencent", "腾讯": "Tencent",
        "bytedance": "ByteDance", "字节跳动": "ByteDance",
        "alibaba": "Alibaba", "aliyun": "Alibaba", "阿里巴巴": "Alibaba",
    }
    if m in mapping:
        return mapping[m]
    for c in canonical_orgs():
        if m == c.lower():
            return c
    return None

def pick_orgs_from_text(text: str) -> List[str]:
    raw = [s.strip() for s in (text or "").split(",") if s.strip()]
    out: List[str] = []
    seen = set()
    for r in raw:
        n = normalize_org(r)
        if n and n not in seen:
            out.append(n)
            seen.add(n)
    return out

def place_pdf(aid: str, src_pdf: str, dest_root: str, date_str: str, orgs: List[str]) -> List[str]:
    ensure_dir(Path(dest_root) / date_str)
    placed: List[str] = []
    for org in orgs:
        org_dir = Path(dest_root) / date_str / org
        ensure_dir(org_dir)
        dst = str(org_dir / f"{aid}.pdf")
        if Path(dst).exists():
            placed.append(dst)
            continue
        if USE_HARDLINKS:
            try:
                os.link(src_pdf, dst)
                placed.append(dst)
                continue
            except Exception:
                pass
        shutil.copy2(src_pdf, dst)
        placed.append(dst)
    return placed

def detect_orgs_for_pdf(pdf_path: str, model: str = "qwen-long") -> List[str]:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or ""
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    client = OpenAI(api_key=api_key, base_url=base_url)
    fobj = client.files.create(file=Path(pdf_path), purpose="file-extract")
    allow = ", ".join(canonical_orgs())
    prompt = "只回答机构名称，限定在以下列表之内，多个用英文逗号分隔；若不确定回答 Unknown。列表：" + allow
    comp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "system", "content": f"fileid://{fobj.id}"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    text = ""
    if comp.choices and comp.choices[0].message and comp.choices[0].message.content:
        text = comp.choices[0].message.content.strip()
    return pick_orgs_from_text(text)

def find_original_pdf(base_name: str, search_root: str) -> str | None:
    target = base_name + ".pdf"
    for p in Path(search_root).rglob("*.pdf"):
        if p.name == target:
            return str(p)
    return None

def process_split_dir(split_dir: str, original_root: str, dest_root: str = "data", model: str = "qwen-long", date_str: str | None = None) -> None:
    date_out = date_str or (now_local().date().isoformat())
    for s in Path(split_dir).glob("*.pdf"):
        name = s.name
        base = name
        if base.endswith(".pdf"):
            base = base[:-4]
        base = base.replace(".p1", "").replace(".p2", "").replace(".p3", "")
        orgs = detect_orgs_for_pdf(str(s), model=model)
        if not orgs:
            continue
        orig = find_original_pdf(base, original_root)
        if not orig:
            continue
        aid = Path(base).stem
        place_pdf(aid, orig, dest_root, date_out, orgs)

if __name__ == "__main__":
    import argparse
    pa = argparse.ArgumentParser()
    pa.add_argument("--split-dir", required=True)
    pa.add_argument("--original-root", required=True)
    pa.add_argument("--dest-root", default="data")
    pa.add_argument("--model", default="qwen-long")
    pa.add_argument("--date", default=None)
    args = pa.parse_args()
    process_split_dir(args.split_dir, args.original_root, dest_root=args.dest_root, model=args.model, date_str=args.date)
