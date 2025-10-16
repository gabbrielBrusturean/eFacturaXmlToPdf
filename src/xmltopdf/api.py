from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import tempfile
import shutil
from typing import List
from pathlib import Path
from . import converter
from .settings import settings

app = FastAPI(title=settings.app_name)

@app.post("/convert/", response_class=FileResponse)
async def convert(files: List[UploadFile] = File(...),
                  oauth: bool = False,
                  token: str | None = None,
                  val1: str = "FACT1",
                  novld: bool = False,
                  set_all_as_pdf: bool = False):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    temp_dir = Path(tempfile.mkdtemp())
    try:
        xml_paths = []
        for f in files:
            dest = temp_dir / f.filename
            with open(dest, "wb") as out:
                content = await f.read()
                out.write(content)
            xml_paths.append(dest)
        out_pdf_dir = temp_dir / "out"
        out_pdf_dir.mkdir(exist_ok=True)
        result = converter.convert_files(
            xml_paths,
            out_pdf_dir,
            use_oauth=oauth,
            val1=val1,
            novld=novld,
            token=token,
            timeout=settings.timeout,
            set_all_as_pdf=set_all_as_pdf,
            merged_name="result.pdf"
        )
        if set_all_as_pdf and result.get("merged_ok"):
            return FileResponse(result["merged_path"], filename="result.pdf", media_type="application/pdf")
        created = result.get("created", [])
        if len(created) == 1:
            return FileResponse(created[0], filename=created[0].name, media_type="application/pdf")
        if created:
            merged = out_pdf_dir / "result.pdf"
            merged_ok, merged_msg = converter.merge_pdfs(created, merged)
            if merged_ok:
                return FileResponse(merged, filename="result.pdf", media_type="application/pdf")
            raise HTTPException(status_code=500, detail=f"Merge failed: {merged_msg}")
        raise HTTPException(status_code=500, detail="No PDFs were produced by conversion.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)