# xmlToPdf

API și utilitar pentru convertirea eFactura XML -> PDF folosind ANAF FCTEL transformare endpoint.

Structură:
- src/xmltopdf: cod sursă (converter + API)
- tests: pytest

Instalare (virtualenv / pip):
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

sau cu Poetry:
pip install poetry
poetry install

Rulare API (dezvoltare):
uvicorn src.xmltopdf.api:app --reload --port 8080

CLI:
python xmlToPdf.py <fișier|director> -o out_dir --setAllAsPDF

Testare:
pytest -q