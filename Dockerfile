FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
RUN apt-get update && apt-get install -y gcc libxml2-dev libxslt-dev build-essential && \
    python -m pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-root --no-interaction

COPY . .

EXPOSE 8080
CMD ["uvicorn", "src.xmltopdf.api:app", "--host", "0.0.0.0", "--port", "8080"]