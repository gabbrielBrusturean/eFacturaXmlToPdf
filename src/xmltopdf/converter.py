from __future__ import annotations
from pathlib import Path
import time
from typing import Iterable, Optional, Tuple, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NOAUTH_BASE = "https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare"
OAUTH_BASE  = "https://api.anaf.ro/prod/FCTEL/rest/transformare"

def make_session(timeout: int = 60) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("POST",),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.request = _wrap_with_timeout(s.request, timeout)
    return s

def _wrap_with_timeout(func, timeout: int):
    def inner(method, url, **kw):
        kw.setdefault("timeout", timeout)
        return func(method, url, **kw)
    return inner

def build_url(use_oauth: bool, val1: str, novld_da: bool) -> str:
    base = OAUTH_BASE if use_oauth else NOAUTH_BASE
    return f"{base}/{val1}/{'DA' if novld_da else ''}".rstrip("/")

def convert_one_xml_bytes(session: requests.Session, url: str, xml_bytes: bytes, bearer_token: Optional[str] = None) -> Tuple[bool, bytes | str]:
    headers = {"Content-Type": "text/plain", "Accept": "application/pdf"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    r = session.post(url, data=xml_bytes, headers=headers)
    ct = (r.headers.get("Content-Type") or "").lower()
    if r.ok and ct.startswith("application/pdf"):
        return True, r.content
    return False, (r.text[:500] if ("text" in ct or "json" in ct or "xml" in ct) else f"{ct} {len(r.content)} bytes")

def convert_paths(
    inputs: Iterable[Path],
    out_dir: Path,
    url: str,
    token: Optional[str],
    timeout: int = 60,
    sleep_between: float = 0.0,
) -> List[Path]:
    session = make_session(timeout=timeout)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    inputs = list(inputs)
    for i, xml in enumerate(inputs, 1):
        pdf_path = out_dir / (xml.stem + ".pdf")
        ok, payload = convert_one_xml_bytes(session, url, xml.read_bytes(), token)
        if ok:
            pdf_path.write_bytes(payload)  # type: ignore[arg-type]
            created.append(pdf_path)
        else:
            print(f"[WARN] Fail {xml.name}: {payload}")
        if sleep_between and i < len(inputs):
            time.sleep(sleep_between)
    return created

# pypdf 6.x: PdfWriter.append pentru merge
try:
    from pypdf import PdfWriter
except Exception:
    PdfWriter = None  # type: ignore[assignment]

def merge_pdfs(pdf_paths: List[Path], merged_path: Path) -> Tuple[bool, str]:
    if PdfWriter is None:
        return False, "pypdf missing: pip install pypdf"
    if not pdf_paths:
        return False, "no PDFs to merge"
    try:
        writer = PdfWriter()
        for p in sorted(pdf_paths, key=lambda x: x.name.lower()):
            writer.append(str(p))
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        with open(merged_path, "wb") as f:
            writer.write(f)
        return True, str(merged_path)
    except Exception as e:
        return False, f"merge error: {e}"
