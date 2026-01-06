from __future__ import annotations

import argparse
import json
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Callable

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# -----------------------------
# Utils
# -----------------------------
def today_str() -> str:
    return datetime.now().date().isoformat()


def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def chunks(seq: list[Any], n: int) -> Iterable[list[Any]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def backoff_sleep(attempt: int, base: float = 1.0, cap: float = 10.0) -> None:
    time.sleep(min(cap, base * (2 ** (attempt - 1))))


def pick_first_md(zip_path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".md")]
        if not names:
            raise RuntimeError(f"no .md in zip: {zip_path}")
        # 选“路径最浅、名字最短”的 md
        names.sort(key=lambda s: (s.count("/"), len(s)))
        name = names[0]
        raw = zf.read(name)
    return name, raw.decode("utf-8", errors="replace")


def pick_preferred_json(zip_path: Path) -> tuple[str, Any]:
    """
    优先 *content_list.json（更适合喂模型做结构化总结）
    其次 *model.json
    否则第一个 json
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".json")]
        if not names:
            raise RuntimeError(f"no .json in zip: {zip_path}")

        prefer = [n for n in names if n.lower().endswith("content_list.json")]
        if not prefer:
            prefer = [n for n in names if n.lower().endswith("model.json")]

        cand = prefer or names
        cand.sort(key=lambda s: (s.count("/"), len(s)))
        name = cand[0]
        text = zf.read(name).decode("utf-8", errors="replace")

    try:
        return name, json.loads(text)
    except Exception:
        return name, text


# -----------------------------
# MinerU Client (Doc-aligned)
# -----------------------------
@dataclass(frozen=True)
class BatchApplyResult:
    batch_id: str
    file_urls: list[str]


class MinerUClient:
    def __init__(self, base_url: str, token: str, *, timeout: tuple[int, int] = (20, 120)) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "*/*",
            }
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        r = self.session.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"MinerU API error: {data}")
        return data

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"MinerU API error: {data}")
        return data

    # doc: POST /api/v4/file-urls/batch  :contentReference[oaicite:4]{index=4}
    def apply_upload_urls(self, files: list[dict[str, Any]], *, model_version: str, extra: dict[str, Any]) -> BatchApplyResult:
        payload = {"files": files, "model_version": model_version}
        payload.update(extra)
        data = self._post("/api/v4/file-urls/batch", payload)
        out = data.get("data") or {}
        batch_id = out.get("batch_id") or ""
        urls = out.get("file_urls") or []
        if not batch_id or not isinstance(urls, list) or not urls:
            raise RuntimeError(f"unexpected apply response: {data}")
        return BatchApplyResult(batch_id=batch_id, file_urls=[str(u) for u in urls])

    # doc: GET /api/v4/extract-results/batch/{batch_id} :contentReference[oaicite:5]{index=5}
    def get_batch_results(self, batch_id: str) -> dict[str, Any]:
        return self._get(f"/api/v4/extract-results/batch/{batch_id}")


def upload_to_presigned_url(
    file_path: Path,
    put_url: str,
    *,
    max_retries: int = 6,
    timeout: tuple[int, int] = (30, 900),
) -> None:
    """
    文档说明：PUT 上传“无须设置 Content-Type 请求头”。:contentReference[oaicite:6]{index=6}
    这里用最朴素的 requests.put(url, data=f) 来贴近示例。
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with file_path.open("rb") as f:
                r = requests.put(put_url, data=f, timeout=timeout)
            r.raise_for_status()
            return
        except Exception as e:
            last_exc = e
            backoff_sleep(attempt)
    raise RuntimeError(f"upload failed: {file_path.name}. last_exc={last_exc!r}")


def wait_batch_done(
    client: MinerUClient,
    batch_id: str,
    *,
    expected_total: int,
    timeout_sec: int = 900,
    poll_sec: int = 3,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_sec
    last: dict[str, Any] | None = None

    while time.time() < deadline:
        last = client.get_batch_results(batch_id)
        data = last.get("data") or {}
        items = data.get("extract_result") or []
        if not isinstance(items, list):
            items = []

        states: dict[str, int] = {}
        done_or_failed = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            st = str(it.get("state") or "unknown").lower()
            states[st] = states.get(st, 0) + 1
            if st in ("done", "failed"):
                done_or_failed += 1

        print(f"\r[parse] {done_or_failed}/{expected_total} {states}", end="", flush=True)

        if expected_total > 0 and done_or_failed >= expected_total:
            print()
            return [it for it in items if isinstance(it, dict)]

        time.sleep(poll_sec)

    raise TimeoutError(f"batch not finished in time. last={last}")


def download_zip(zip_url: str, token: str, dest: Path, *, max_retries: int = 6) -> None:
    last_exc: Exception | None = None
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(1, max_retries + 1):
        try:
            with requests.get(zip_url, headers=headers, stream=True, timeout=(30, 900)) as r:
                r.raise_for_status()
                with dest.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
            return
        except Exception as e:
            last_exc = e
            backoff_sleep(attempt)
    raise RuntimeError(f"download zip failed. last_exc={last_exc!r}")


def run_local_batch(
    *,
    pdfs: list[Path],
    out_md_root: Path,
    out_json_root: Path,
    base_url: str,
    token: str,
    model_version: str,
    timeout_sec: int,
    poll_sec: int,
    upload_retries: int,
    keep_zip: bool,
    # pipeline params
    is_ocr: bool,
    enable_formula: bool,
    enable_table: bool,
    language: str,
     extra_formats: list[str],
     page_ranges: str | None,
     batch_size: int = 10,
     upload_concurrency: int = 10,
     limit_files: int = 0,
     on_json: Callable[[Path], None] | None = None,
     skip_existing: bool = False,
) -> None:
    if limit_files and limit_files > 0:
        pdfs = pdfs[:limit_files]
    date_dir = today_str()
    out_md_dir = ensure_dir(out_md_root / date_dir)
    out_json_dir = ensure_dir(out_json_root / date_dir)
    tmp_zip_dir = ensure_dir(out_md_dir / "_tmp_zip")

    client = MinerUClient(base_url, token)

    # --- build request body (doc-aligned) ---
    # files: [{"name": "...pdf", "data_id": "...", "page_ranges": "...", "is_ocr": ...}, ...] :contentReference[oaicite:8]{index=8}
    files_payload: list[dict[str, Any]] = []
    for p in pdfs:
        one = {"name": p.name, "data_id": p.stem}
        if page_ranges:
            one["page_ranges"] = page_ranges
        if model_version == "pipeline":
            one["is_ocr"] = bool(is_ocr)
        files_payload.append(one)

    extra: dict[str, Any] = {}
    if model_version == "pipeline":
        extra.update(
            {
                "enable_formula": bool(enable_formula),
                "enable_table": bool(enable_table),
                "language": language,
            }
        )
    if extra_formats:
        extra["extra_formats"] = extra_formats  # docx/html/latex（markdown/json 默认） :contentReference[oaicite:9]{index=9}

    if skip_existing:
        _filtered = []
        for p in pdfs:
            _md = out_md_dir / f"{p.stem}.md"
            _js = out_json_dir / f"{p.stem}.json"
            if _md.exists() and _js.exists():
                continue
            _filtered.append(p)
        pdfs = _filtered
    for pdf_chunk in chunks(pdfs, max(1, batch_size)):
        # 对齐 chunk 的 files payload
        chunk_payload = []
        for p in pdf_chunk:
            one = {"name": p.name, "data_id": p.stem}
            if page_ranges:
                one["page_ranges"] = page_ranges
            if model_version == "pipeline":
                one["is_ocr"] = bool(is_ocr)
            chunk_payload.append(one)

        applied = client.apply_upload_urls(chunk_payload, model_version=model_version, extra=extra)

        total = len(pdf_chunk)
        done = 0
        def _one(idx: int) -> None:
            upload_to_presigned_url(pdf_chunk[idx], applied.file_urls[idx], max_retries=upload_retries)
        with ThreadPoolExecutor(max_workers=max(1, upload_concurrency)) as ex:
            futs = [ex.submit(_one, i) for i in range(total)]
            for _ in as_completed(futs):
                done += 1
                print(f"\r[upload] {done}/{total}", end="", flush=True)
        print()

        # 2) poll
        results = wait_batch_done(
            client,
            applied.batch_id,
            expected_total=len(pdf_chunk),
            timeout_sec=timeout_sec,
            poll_sec=poll_sec,
        )

        # 3) download + extract
        # 用 file_name / data_id 来匹配
        by_name = {str(it.get("file_name") or ""): it for it in results}
        by_dataid = {str(it.get("data_id") or ""): it for it in results}

        wrote = 0
        total_write = len(pdf_chunk)
        for p in pdf_chunk:
            it = by_dataid.get(p.stem) or by_name.get(p.name)
            if not it:
                print(f"[skip] no result item for {p.name}")
                continue

            state = str(it.get("state") or "").lower()
            if state != "done":
                print(f"[skip] {p.name} state={state} err={it.get('err_msg')}")
                continue

            zip_url = it.get("full_zip_url")
            if not zip_url:
                print(f"[skip] {p.name} has no full_zip_url")
                continue

            zip_path = tmp_zip_dir / f"{p.stem}.zip"
            download_zip(zip_url, token, zip_path)

            # md
            _, md_text = pick_first_md(zip_path)
            (out_md_dir / f"{p.stem}.md").write_text(md_text, encoding="utf-8")

            # json
            _, obj = pick_preferred_json(zip_path)
            if isinstance(obj, str):
                (out_json_dir / f"{p.stem}.json").write_text(obj, encoding="utf-8")
            else:
                (out_json_dir / f"{p.stem}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            if on_json:
                try:
                    on_json(out_json_dir / f"{p.stem}.json")
                except Exception:
                    pass
            wrote += 1
            print(f"\r[write] {wrote}/{total_write}", end="", flush=True)

            if not keep_zip:
                try:
                    zip_path.unlink(missing_ok=True)
                except Exception:
                    pass
            print()

    if not keep_zip:
        try:
            tmp_zip_dir.rmdir()
        except Exception:
            pass

def main() -> None:
    pa = argparse.ArgumentParser("pdf2md (MinerU local batch)")
    pa.add_argument("--input-dir", default="cache_pdfs", help="放 pdf 的目录")
    pa.add_argument("--out-md-root", default=str(Path("data") / "md"))
    pa.add_argument("--out-json-root", default=str(Path("data") / "json"))
    pa.add_argument("--base-url", default=os.environ.get("MINERU_BASE_URL", "https://mineru.net"))
    pa.add_argument("--token", default=os.environ.get("MINERU_TOKEN", ""))
    pa.add_argument("--token-file", default=str(Path("config") / "mineru.txt"))

    pa.add_argument("--model-version", default=os.environ.get("MINERU_MODEL_VERSION", "vlm"), choices=["vlm", "pipeline"])
    pa.add_argument("--timeout-sec", type=int, default=900)
    pa.add_argument("--poll-sec", type=int, default=3)
    pa.add_argument("--upload-retries", type=int, default=6)
    pa.add_argument("--keep-zip", action="store_true")
    pa.add_argument("--batch-size", type=int, default=10)
    pa.add_argument("--upload-concurrency", type=int, default=10)
    pa.add_argument("--limit-files", type=int, default=0)

    # pipeline only (文档：仅 pipeline 有效) :contentReference[oaicite:11]{index=11}
    pa.add_argument("--is-ocr", action="store_true", help="pipeline: 启用 OCR")
    pa.add_argument("--enable-formula", action="store_true", help="pipeline: 开启公式识别（默认 true）")
    pa.add_argument("--enable-table", action="store_true", help="pipeline: 开启表格识别（默认 true）")
    pa.add_argument("--language", default="ch", help="pipeline: 语言")
    pa.add_argument("--extra-formats", default="", help="额外导出格式：docx,html,latex（markdown/json 默认）")
    pa.add_argument("--page-ranges", default="", help='页码范围，比如 "2,4-6" 或 "1-600"')

    args = pa.parse_args()

    token = (args.token or "").strip()
    if not token:
        p = Path(args.token_file)
        if p.exists():
            token = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not token:
        raise SystemExit("MinerU token is required: set MINERU_TOKEN or put into config/mineru.txt")

    in_dir = Path(args.input_dir)
    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no pdfs found in {in_dir}")

    extra_formats = [x.strip() for x in args.extra_formats.split(",") if x.strip()]
    page_ranges = args.page_ranges.strip() or None

    # pipeline 默认 enable_formula/table 是 true；这里如果你不传，就保持 True
    enable_formula = True if not args.enable_formula else True
    enable_table = True if not args.enable_table else True

    run_local_batch(
        pdfs=pdfs,
        out_md_root=Path(args.out_md_root),
        out_json_root=Path(args.out_json_root),
        base_url=args.base_url,
        token=token,
        model_version=args.model_version,
        timeout_sec=args.timeout_sec,
        poll_sec=args.poll_sec,
        upload_retries=args.upload_retries,
        keep_zip=args.keep_zip,
        is_ocr=bool(args.is_ocr),
        enable_formula=bool(enable_formula),
        enable_table=bool(enable_table),
        language=args.language,
        extra_formats=extra_formats,
        page_ranges=page_ranges,
        batch_size=args.batch_size,
        upload_concurrency=args.upload_concurrency,
        limit_files=args.limit_files,
    )


if __name__ == "__main__":
    main()
