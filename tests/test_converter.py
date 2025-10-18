from pathlib import Path
from xmltopdf.converter import merge_pdfs

def test_merge_pdfs_empty(tmp_path: Path):
    ok, msg = merge_pdfs([], tmp_path / "out.pdf")
    assert not ok
    assert "no PDFs" in msg
