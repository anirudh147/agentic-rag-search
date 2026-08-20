# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# System deps: libpq for psycopg2, build tools for a couple of native wheels,
# and the small set of shared libs Docling's layout/OCR stack needs at
# runtime (libgl/libglib for opencv, which docling-ibm-models depends on).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cache directory for Docling's downloaded layout/table-structure models so
# repeated container restarts don't re-download them (mount as a volume in
# docker-compose.yml).
ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface /data/source_documents /data/eval_reports

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
