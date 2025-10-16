from pathlib import Path
from src.xmltopdf import converter
import tempfile

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
except Exception:
    canvas = None

def _make_sample_pdf(path: Path, text: str = "hello"):
    if canvas is None:
        path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 200 200] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 10 100 Td (hello) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000116 00000 n \n0000000211 00000 n \ntrailer\n<< /Root 1 0 R >>\nstartxref\n312\n%%EOF")
        return
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(100, 750, text)
    c.showPage()
    c.save()

def test_merge_pdfs_creates_merged_file(tmp_path):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_sample_pdf(a, "A")
    _make_sample_pdf(b, "B")
    merged = tmp_path / "merged.pdf"
    ok, msg = converter.merge_pdfs([a, b], merged)
    assert ok, msg
    assert merged.exists()
    assert merged.stat().st_size > 0