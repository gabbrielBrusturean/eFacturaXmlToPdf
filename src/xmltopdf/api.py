from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from .converter import build_url, convert_one_xml_bytes, convert_paths, merge_pdfs, make_session
from .settings import settings

app = FastAPI(title="xmlToPdf Service", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/convert/single", response_class=StreamingResponse)
async def convert_single(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(400, "Upload must be an .xml file")
    xml_bytes = await file.read()
    url = build_url(settings.use_oauth, settings.val1, settings.novld)
    session = make_session(timeout=settings.timeout)
    ok, payload = convert_one_xml_bytes(session, url, xml_bytes, settings.bearer_token)
    if not ok:
        raise HTTPException(502, f"ANAF transform failed: {payload}")
    return StreamingResponse(iter([payload]), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.pdf"'
    })

@app.post("/convert/batch")
async def convert_batch(files: List[UploadFile] = File(...), merge: bool = False):
    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        xml_paths: List[Path] = []
        for f in files:
            if not f.filename.lower().endswith(".xml"):
                continue
            p = tmp / f.filename
            p.write_bytes(await f.read())
            xml_paths.append(p)
        if not xml_paths:
            raise HTTPException(400, "no .xml files provided")

        out_dir = tmp / "out"
        url = build_url(settings.use_oauth, settings.val1, settings.novld)
        created = convert_paths(xml_paths, out_dir, url, settings.bearer_token, settings.timeout, settings.sleep_between)

        if merge:
            merged = out_dir / "all_in_one.pdf"
            ok, msg = merge_pdfs(created, merged)
            if not ok:
                raise HTTPException(500, f"merge failed: {msg}")
            return StreamingResponse(open(merged, "rb"), media_type="application/pdf",
                                     headers={"Content-Disposition": 'attachment; filename="all_in_one.pdf"'})
        return JSONResponse({"generated": [p.name for p in created]})
