from typing import Iterable, List, Optional, Tuple
from pathlib import Path
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .settings import settings
import os

# pypdf import / graceful fallback
try:
    import pypdf
    from pypdf import PdfWriter
except Exception:
    PdfWriter = None

def _wrap_request_with_timeout(func, timeout: int):
    def inner(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return func(method, url, **kwargs)
    return inner

def make_session(timeout: int = None) -> requests.Session:
    if timeout is None:
        timeout = settings.timeout
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("POST",),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.request = _wrap_request_with_timeout(s.request, timeout=timeout)
    return s

def build_url(use_oauth: bool, val1: str, novld_da: bool) -> str:
    base = settings.oauth_base if use_oauth else settings.noauth_base
    val2 = "DA" if novld_da else ""
    if not val2:
        return f"{base}/{val1}"
    return f"{base}/{val1}/{val2}"

def try_convert_one(session: requests.Session, url: str, xml_path: Path, out_pdf: Path, bearer_token: Optional[str]) -> Tuple[bool, str]:
    xml_bytes = xml_path.read_bytes()
    headers = {
        "Content-Type": "text/plain",
        "Accept": "application/pdf",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    r = session.post(url, data=xml_bytes, headers=headers)
    ct = (r.headers.get("Content-Type") or "").lower()
    if r.ok and ct.startswith("application/pdf"):
        out_pdf.write_bytes(r.content)
        return True, f"OK {r.status_code}"
    preview = r.text[:500] if ("text" in ct or "json" in ct or "xml" in ct) else f"<{ct} {len(r.content)} bytes>"
    return False, f"HTTP {r.status_code} {ct} :: {preview}"

def merge_pdfs(pdf_paths: List[Path], merged_path: Path) -> Tuple[bool, str]:
    if PdfWriter is None:
        return False, "Missing 'pypdf' (PdfWriter). Install with: python -m pip install -U pypdf"
    if not pdf_paths:
        return False, "No PDFs to merge."
    try:
        writer = PdfWriter()
        for p in pdf_paths:
            writer.append(str(p))
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        with open(merged_path, "wb") as f:
            writer.write(f)
        return True, f"Merged -> {merged_path}"
    except Exception as e:
        return False, f"Merge error: {e}"

def convert_files(xml_paths: Iterable[Path],
                  out_dir: Path,
                  use_oauth: bool = False,
                  val1: str = "FACT1",
                  novld: bool = False,
                  token: Optional[str] = None,
                  timeout: Optional[int] = None,
                  sleep_between: float = 0.0,
                  set_all_as_pdf: bool = False,
                  merged_name: str = "all_in_one.pdf") -> dict:
    session = make_session(timeout=timeout or settings.timeout)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = list(xml_paths)
    if not targets:
        return {"ok": 0, "fail": 0, "created": [], "msg": "No XML files provided."}

    url = build_url(use_oauth=use_oauth, val1=val1, novld_da=novld)
    ok = fail = 0
    created_pdfs: List[Path] = []

    for i, xml in enumerate(targets, 1):
        out_pdf = out_dir / (xml.stem + ".pdf")
        success, msg = try_convert_one(session, url, xml, out_pdf, token)
        print(f"[{i}/{len(targets)}] {'✔' if success else '✖'} {xml.name} -> {out_pdf.name} :: {msg}")
        if success:
            ok += 1
            created_pdfs.append(out_pdf)
        else:
            fail += 1
        if sleep_between > 0 and i < len(targets):
            time.sleep(sleep_between)

    result = {"ok": ok, "fail": fail, "created": created_pdfs, "out_dir": str(out_dir)}

    if set_all_as_pdf:
        created_pdfs.sort(key=lambda p: p.name.lower())
        merged_path = out_dir / merged_name
        merged_ok, merged_msg = merge_pdfs(created_pdfs, merged_path)
        result["merged_ok"] = merged_ok
        result["merged_msg"] = merged_msg
        result["merged_path"] = str(merged_path) if merged_ok else None

    return result