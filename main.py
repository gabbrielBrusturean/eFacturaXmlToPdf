#!/usr/bin/env python3
# thin CLI wrapper that delegates to src.xmltopdf.converter.convert_files

import argparse
import sys
from pathlib import Path
from src.xmltopdf import converter

def main():
    ap = argparse.ArgumentParser(description="Wrapper CLI for xml->pdf (delegates to src.xmltopdf.converter)")
    ap.add_argument("input", help="Fișier .xml sau director cu .xml-uri")
    ap.add_argument("-o", "--out", default="out_pdf", help="Director ieșire (default: out_pdf)")
    ap.add_argument("--oauth", action="store_true", help="Use oauth endpoint")
    ap.add_argument("--token", default=None, help="Bearer token")
    ap.add_argument("--val1", default="FACT1")
    ap.add_argument("--novld", action="store_true")
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument("--setAllAsPDF", action="store_true")
    ap.add_argument("--merged-name", default="all_in_one.pdf")
    args = ap.parse_args()

    input_path = Path(args.input)
    if input_path.is_file():
        targets = [input_path]
    else:
        targets = sorted(input_path.rglob("*.xml"))

    out_dir = Path(args.out)
    result = converter.convert_files(
        targets,
        out_dir,
        use_oauth=args.oauth,
        val1=args.val1,
        novld=args.novld,
        token=args.token,
        timeout=args.timeout,
        sleep_between=args.sleep,
        set_all_as_pdf=args.setAllAsPDF,
        merged_name=args.merged_name,
    )
    if result.get("ok", 0) == 0:
        print("No successful conversions.", file=sys.stderr)
        sys.exit(2)
    print("Done.")
    sys.exit(0)

if __name__ == "__main__":
    main()
