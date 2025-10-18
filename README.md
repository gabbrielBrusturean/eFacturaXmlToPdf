# eFactura XML → PDF (ANAF)

Serviciu și CLI pentru conversia fișierelor eFactura **XML → PDF** folosind endpoint-ul ANAF:
`/prod/FCTEL/rest/transformare/{val1}/{val2}` (Content-Type: `text/plain`).

## Endpoint-uri
- `POST /convert/single` – 1 fișier XML → PDF (download)
- `POST /convert/batch?merge=true` – mai multe XML → `all_in_one.pdf`
- `GET /health` – status

## Rulare local (fără Docker)
```bash
pip install -r requirements.txt
uvicorn src.xmltopdf.api:app --host 0.0.0.0 --port 8000 --reload
# Swagger: http://localhost:8000/docs
