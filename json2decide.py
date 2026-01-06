from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict

from openai import OpenAI


def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def today_str() -> str:
    return datetime.now().date().isoformat()



def load_first_pages_text(json_path: Path, max_page_idx: int = 2) -> str:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("items") or []
    else:
        items = data
    lines: List[str] = []
    for it in items:
        try:
            if int(it.get("page_idx", 0)) <= max_page_idx:
                t = str(it.get("text") or "")
                tp = str(it.get("type") or "")
                if tp in ("text", "aside_text", "list"):
                    if tp == "list" and isinstance(it.get("list_items"), list):
                        lines.extend([str(x) for x in it["list_items"]])
                    elif t:
                        lines.append(t)
        except Exception:
            continue
    return "\n".join(lines).strip()


def call_qwen_plus(api_key: str, base_url: str, model: str, content: str, file_name: str, sys_prompt: str | None = None) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    if not sys_prompt:
        sys_prompt = (
            "你是一个严谨的机构识别助手。仅根据给出的论文前两页文本，识别第一作者与通讯作者各自所属的机构名称（如大学或公司），并从两者中挑选一个最主要的机构作为最终机构。"
            "判断规则：若能识别到通讯作者（例如 *、† 或脚注“Corresponding author”），优先选择通讯作者机构；否则选择第一作者机构。"
            "输出只返回一个 JSON 对象，至少包含键：文件名、机构名、is_large；且建议同时包含第一作者机构与通讯作者机构两个字段以便审阅。"
            "机构名尽量使用中文名称；若无法确定中文名称则保留原文。对于 Google、Meta、Kimi 等全球知名品牌，请保留英文原文，不要翻译。"
            "is_large 为布尔值，true 表示该机构为全球范围内广泛认可的大型或行业可信机构。"
            "只返回 JSON，不要输出其他文本。"
        )
    user_content = f"文件名：{file_name}\n文本：\n{content}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ],
        stream=False,
    )
    out = resp.choices[0].message.content if resp.choices else "{}"
    try:
        obj = json.loads(out)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"文件名": file_name, "机构名": "", "is_large": False}


def append_result(out_path: Path, item: Dict[str, Any]) -> None:
    if out_path.exists():
        try:
            text = out_path.read_text(encoding="utf-8")
            obj = json.loads(text)
            if isinstance(obj, list):
                obj.append(item)
                out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
                return
            else:
                out_path.write_text(json.dumps([obj, item], ensure_ascii=False, indent=2), encoding="utf-8")
                return
        except Exception:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            return
    else:
        out_path.write_text(json.dumps([item], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    pa = argparse.ArgumentParser("json2decide")
    pa.add_argument("--input", default="")
    pa.add_argument("--out-root", default=str(Path("data_output") / "decide"))
    args = pa.parse_args()

    model = "qwen-plus"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dep_path = Path("config") / "configDepositary.py"
    if dep_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("configDepositary", str(dep_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            base_url = getattr(mod, "org_base_url", base_url)
            model = getattr(mod, "org_model", model)
    api_key_path = Path("config") / "qwen_api.txt"
    if not api_key_path.exists():
        raise SystemExit(f"缺少 API Key 文件：{api_key_path}")
    api_key = api_key_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not api_key:
        raise SystemExit(f"API Key 文件为空：{api_key_path}")

    out_dir = ensure_dir(Path(args.out_root))
    out_path = out_dir / f"{today_str()}.json"

    inputs: list[Path] = []
    if args.input.strip():
        p = Path(args.input.strip())
        if not p.exists():
            raise SystemExit(f"输入路径不存在：{p}")
        if p.is_dir():
            inputs = sorted(p.glob("*.json"))
        else:
            inputs = [p]
    else:
        default_dir = Path("data") / "json" / today_str()
        if not default_dir.exists():
            raise SystemExit(f"默认输入目录不存在：{default_dir}")
        inputs = sorted(default_dir.glob("*.json"))
        if not inputs:
            raise SystemExit(f"默认输入目录无 json 文件：{default_dir}")

    for in_path in inputs:
        text = load_first_pages_text(in_path, max_page_idx=2)
        item = call_qwen_plus(api_key, base_url, model, text, file_name=in_path.name)
        append_result(out_path, item)

    print(str(out_path))


if __name__ == "__main__":
    main()
