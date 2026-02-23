# Financial Data Lakehouse - Cloud Run Job (ingestión yfinance → GCS → BigQuery)
# Python 3.12 slim para tamaño reducido
FROM python:3.12-slim

WORKDIR /app

# Dependencias: copiar primero para aprovechar caché de capas
COPY src/requirements.txt src/requirements.txt
RUN pip install --no-cache-dir -r src/requirements.txt

# Código del pipeline
COPY src/ src/

# Cloud Run inyecta GCS_BUCKET, BQ_PROJECT, BQ_DATASET_*; no se necesita entrypoint extra
CMD ["python", "-m", "src.main"]
