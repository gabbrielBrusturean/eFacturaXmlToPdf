FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# user non-root (mai sigur)
RUN useradd -m appuser

WORKDIR /app

# deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# cod
COPY src/ /app/src/
ENV PYTHONPATH=/app/src

USER appuser
EXPOSE 8000

CMD ["uvicorn", "xmltopdf.api:app", "--host", "0.0.0.0", "--port", "8000"]
