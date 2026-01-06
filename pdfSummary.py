from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List

from openai import OpenAI
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
    p = Path("config") / "qwen_api.txt"
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise SystemExit(f"API Key 文件为空：{p}")
    return text


def make_client(api_key: str | None = None, base_url: str | None = None) -> OpenAI:
    k = api_key or load_api_key()
    if base_url:
        u = base_url
    else:
        u = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        try:
            dep = Path("config") / "configDepositary.py"
            if dep.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("configDepositary", str(dep))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    u = getattr(mod, "summary_base_url", u)
        except Exception:
            pass
    return OpenAI(api_key=k, base_url=u)

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


def summarize_md(client: OpenAI, model: str, md_text: str, file_name: str, system_prompt: str | None = None, user_prompt_prefix: str | None = None) -> str:
    example = load_summary_example()
    if system_prompt:
        sys_prompt = system_prompt
    else:
        sys_prompt = (
            "你是一个论文总结助手。参考示例的风格与结构，对给定的 Markdown 论文进行中文总结。"
            "仅输出纯文本，总结包含：机构、标题、来源、文章简介、重点思路、分析总结或个人观点。"
            f"\n示例：\n{example}"
        )
    user_content = md_text if not user_prompt_prefix else f"{user_prompt_prefix}\n{md_text}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ],
        stream=False,
    )
    return resp.choices[0].message.content if resp.choices else ""


def main() -> None:
    pa = argparse.ArgumentParser("pdfSummary")
    pa.add_argument("--input-dir", default="")
    pa.add_argument("--out-root", default=str(Path("dataSelect")))
    default_model = "qwen2.5-72b-instruct"
    try:
        dep = Path("config") / "configDepositary.py"
        if dep.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("configDepositary", str(dep))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                default_model = getattr(mod, "summary_model", default_model)
    except Exception:
        pass
    pa.add_argument("--model", default=default_model)
    args = pa.parse_args()

    date_str = today_str()
    md_root = Path(args.input_dir.strip()) if args.input_dir.strip() else Path("dataSelect") / "md" / date_str
    if not md_root.exists():
        raise SystemExit(f"输入目录不存在：{md_root}")
    files = list_md_files(md_root)
    if not files:
        raise SystemExit(f"输入目录无 md 文件：{md_root}")

    client = make_client()

    out_summary_dir = ensure_dir(Path(args.out_root) / "summary" / date_str)
    out_gather_dir = ensure_dir(Path(args.out_root) / "summary_gather")
    out_gather_path = out_gather_dir / f"{date_str}.txt"

    for p in files:
        one_out = out_summary_dir / f"{p.stem}.txt"
        if one_out.exists():
            continue
        md_text = p.read_text(encoding="utf-8", errors="ignore")
        s = summarize_md(client, args.model, md_text, file_name=p.name)
        one_out.write_text(s, encoding="utf-8")
        with out_gather_path.open("a", encoding="utf-8") as f:
            f.write(s)
            f.write("\n\n############################################################\n\n\n")

    print(str(out_summary_dir))
    print(str(out_gather_path))


if __name__ == "__main__":
    main()
