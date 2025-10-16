#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# DEBUG: vezi ce versiune de pypdf ai și importă PdfWriter (pypdf 6.x)
try:
    import pypdf
    print("[DEBUG] pypdf:", getattr(pypdf, "__version__", "?"), "from", getattr(pypdf, "__file__", "?"))
    from pypdf import PdfWriter
except Exception as e:
    print("[DEBUG] pypdf import failed:", repr(e))
    PdfWriter = None

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
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.request = _wrap_request_with_timeout(s.request, timeout=timeout)
    return s

def _wrap_request_with_timeout(func, timeout: int):
    def inner(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return func(method, url, **kwargs)
    return inner

def build_url(use_oauth: bool, val1: str, novld_da: bool) -> str:
    base = OAUTH_BASE if use_oauth else NOAUTH_BASE
    val2 = "DA" if novld_da else ""
    if not val2:
        return f"{base}/{val1}"
    return f"{base}/{val1}/{val2}"

def try_convert_one(session: requests.Session, url: str, xml_path: Path, out_pdf: Path, bearer_token: str | None):
    xml_bytes = xml_path.read_bytes()
    headers = {
        "Content-Type": "text/plain",  # conform specificației
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

def merge_pdfs(pdf_paths: list[Path], merged_path: Path) -> tuple[bool, str]:
    if PdfWriter is None:
        return False, "Lipsește pachetul 'pypdf' sau importul a eșuat. Instalează/verify: python -m pip install -U pypdf"
    if not pdf_paths:
        return False, "Nu există PDF-uri de îmbinat (toate conversiile au eșuat?)."
    try:
        writer = PdfWriter()
        for p in pdf_paths:
            # pypdf 6.x: append atașează toate paginile din PDF
            writer.append(str(p))
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        with open(merged_path, "wb") as f:
            writer.write(f)
        return True, f"Îmbinate în {merged_path}"
    except Exception as e:
        return False, f"Eroare la îmbinare: {e}"

def convert_path(input_path: Path, out_dir: Path, url: str, token: str | None,
                 timeout: int, sleep_between: float, set_all_as_pdf: bool, merged_name: str):
    session = make_session(timeout=timeout)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.xml"))
    if not targets:
        print("Nu am găsit fișiere .xml.", file=sys.stderr)
        sys.exit(2)

    ok = fail = 0
    created_pdfs: list[Path] = []

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

    print(f"\nRezumat conversie: {ok} reușite, {fail} eșecuri. PDF-urile: {out_dir}")

    if set_all_as_pdf:
        created_pdfs.sort(key=lambda p: p.name.lower())
        merged_path = out_dir / merged_name
        merged_ok, merged_msg = merge_pdfs(created_pdfs, merged_path)
        status = "✔" if merged_ok else "✖"
        print(f"[MERGE] {status} {merged_msg}")

def main():
    ap = argparse.ArgumentParser(
        description="eFactura XML → PDF via ANAF FCTEL transformare/{val1}/{val2} (Content-Type: text/plain)."
    )
    ap.add_argument("input", help="Fișier .xml sau director cu .xml-uri")
    ap.add_argument("-o", "--out", default="out_pdf", help="Director ieșire (default: out_pdf)")
    ap.add_argument("--oauth", action="store_true",
                    help="Folosește endpoint-ul cu OAuth2 (api.anaf.ro). Necesită --token.")
    ap.add_argument("--token", default=None, help="Bearer token pentru varianta OAuth2.")
    ap.add_argument("--val1", default="FACT1",
                    help="Standard: FACT1 sau FCN (default: FACT1)")
    ap.add_argument("--novld", action="store_true",
                    help="Setează val2=DA (nu validează XML înainte de transformare). Recomandat.")
    ap.add_argument("--timeout", type=int, default=60, help="Timeout request (sec).")
    ap.add_argument("--sleep", type=float, default=0.0, help="Pauză între fișiere (sec).")

    # opțiuni de îmbinare
    ap.add_argument("--setAllAsPDF", action="store_true",
                    help="După conversie, îmbină toate PDF-urile într-un singur fișier.")
    ap.add_argument("--merged-name", default="all_in_one.pdf",
                    help="Numele PDF-ului final (default: all_in_one.pdf)")

    args = ap.parse_args()

    if args.oauth and not args.token:
        print("Eroare: --oauth necesită --token (Bearer).", file=sys.stderr)
        sys.exit(2)

    url = build_url(use_oauth=args.oauth, val1=args.val1, novld_da=args.novld)

    input_path = Path(args.input).resolve()
    out_dir = Path(args.out)
    convert_path(
        input_path, out_dir, url, args.token,
        args.timeout, args.sleep,
        set_all_as_pdf=args.setAllAsPDF,
        merged_name=args.merged_name,
    )

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# DEBUG: vezi ce versiune de pypdf ai și importă PdfWriter (pypdf 6.x)
try:
    import pypdf
    print("[DEBUG] pypdf:", getattr(pypdf, "__version__", "?"), "from", getattr(pypdf, "__file__", "?"))
    from pypdf import PdfWriter
except Exception as e:
    print("[DEBUG] pypdf import failed:", repr(e))
    PdfWriter = None

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
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.request = _wrap_request_with_timeout(s.request, timeout=timeout)
    return s

def _wrap_request_with_timeout(func, timeout: int):
    def inner(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return func(method, url, **kwargs)
    return inner

def build_url(use_oauth: bool, val1: str, novld_da: bool) -> str:
    base = OAUTH_BASE if use_oauth else NOAUTH_BASE
    val2 = "DA" if novld_da else ""
    if not val2:
        return f"{base}/{val1}"
    return f"{base}/{val1}/{val2}"

def try_convert_one(session: requests.Session, url: str, xml_path: Path, out_pdf: Path, bearer_token: str | None):
    xml_bytes = xml_path.read_bytes()
    headers = {
        "Content-Type": "text/plain",  # conform specificației
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

def merge_pdfs(pdf_paths: list[Path], merged_path: Path) -> tuple[bool, str]:
    if PdfWriter is None:
        return False, "Lipsește pachetul 'pypdf' sau importul a eșuat. Instalează/verify: python -m pip install -U pypdf"
    if not pdf_paths:
        return False, "Nu există PDF-uri de îmbinat (toate conversiile au eșuat?)."
    try:
        writer = PdfWriter()
        for p in pdf_paths:
            # pypdf 6.x: append atașează toate paginile din PDF
            writer.append(str(p))
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        with open(merged_path, "wb") as f:
            writer.write(f)
        return True, f"Îmbinate în {merged_path}"
    except Exception as e:
        return False, f"Eroare la îmbinare: {e}"

def convert_path(input_path: Path, out_dir: Path, url: str, token: str | None,
                 timeout: int, sleep_between: float, set_all_as_pdf: bool, merged_name: str):
    session = make_session(timeout=timeout)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.xml"))
    if not targets:
        print("Nu am găsit fișiere .xml.", file=sys.stderr)
        sys.exit(2)

    ok = fail = 0
    created_pdfs: list[Path] = []

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

    print(f"\nRezumat conversie: {ok} reușite, {fail} eșecuri. PDF-urile: {out_dir}")

    if set_all_as_pdf:
        created_pdfs.sort(key=lambda p: p.name.lower())
        merged_path = out_dir / merged_name
        merged_ok, merged_msg = merge_pdfs(created_pdfs, merged_path)
        status = "✔" if merged_ok else "✖"
        print(f"[MERGE] {status} {merged_msg}")

def main():
    ap = argparse.ArgumentParser(
        description="eFactura XML → PDF via ANAF FCTEL transformare/{val1}/{val2} (Content-Type: text/plain)."
    )
    ap.add_argument("input", help="Fișier .xml sau director cu .xml-uri")
    ap.add_argument("-o", "--out", default="out_pdf", help="Director ieșire (default: out_pdf)")
    ap.add_argument("--oauth", action="store_true",
                    help="Folosește endpoint-ul cu OAuth2 (api.anaf.ro). Necesită --token.")
    ap.add_argument("--token", default=None, help="Bearer token pentru varianta OAuth2.")
    ap.add_argument("--val1", default="FACT1",
                    help="Standard: FACT1 sau FCN (default: FACT1)")
    ap.add_argument("--novld", action="store_true",
                    help="Setează val2=DA (nu validează XML înainte de transformare). Recomandat.")
    ap.add_argument("--timeout", type=int, default=60, help="Timeout request (sec).")
    ap.add_argument("--sleep", type=float, default=0.0, help="Pauză între fișiere (sec).")

    # opțiuni de îmbinare
    ap.add_argument("--setAllAsPDF", action="store_true",
                    help="După conversie, îmbină toate PDF-urile într-un singur fișier.")
    ap.add_argument("--merged-name", default="all_in_one.pdf",
                    help="Numele PDF-ului final (default: all_in_one.pdf)")

    args = ap.parse_args()

    if args.oauth and not args.token:
        print("Eroare: --oauth necesită --token (Bearer).", file=sys.stderr)
        sys.exit(2)

    url = build_url(use_oauth=args.oauth, val1=args.val1, novld_da=args.novld)

    input_path = Path(args.input).resolve()
    out_dir = Path(args.out)
    convert_path(
        input_path, out_dir, url, args.token,
        args.timeout, args.sleep,
        set_all_as_pdf=args.setAllAsPDF,
        merged_name=args.merged_name,
    )

if __name__ == "__main__":
    main()
