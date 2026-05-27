FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY pyproject.toml /app/pyproject.toml

ENV PYTHONUNBUFFERED=1 \
    AIG_KEY_DIR=/app/keys \
    AIG_DATABASE_URL=sqlite:////app/data/aig.db

VOLUME ["/app/data", "/app/keys"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
