FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY ai-sdr/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-sdr/backend/ .

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --limit-concurrency 64
