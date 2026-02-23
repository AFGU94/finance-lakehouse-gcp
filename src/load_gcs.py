"""
Carga de datos a Cloud Storage (GCS) en formato Parquet.
Estructura: bucket/raw/YYYY-MM-DD/stock_prices.parquet
"""
import io
import logging
from datetime import datetime, timezone

import pandas as pd

from src.config import get_bq_project, get_gcs_bucket

logger = logging.getLogger(__name__)


def save_to_gcs(df: pd.DataFrame, date_prefix: str | None = None) -> str | None:
    """
    Escribe el DataFrame como Parquet en GCS en raw/YYYY-MM-DD/.

    Args:
        df: DataFrame con columnas de stock (date, symbol, open, high, ...).
        date_prefix: Fecha para el path, formato YYYY-MM-DD. Si None, usa hoy.

    Returns:
        URI gs://bucket/raw/YYYY-MM-DD/stock_prices.parquet o None si falla.
    """
    if df is None or df.empty:
        logger.warning("Empty DataFrame, skipping GCS upload")
        return None

    bucket_name = get_gcs_bucket()
    project = get_bq_project()
    if not bucket_name:
        logger.error("GCS_BUCKET not set")
        return None
    if not project:
        logger.error("BQ_PROJECT not set (necesario para el cliente GCS)")
        return None

    # BigQuery no acepta nombres de columna como tuplas (ej. ('date','')); asegurar strings planos
    df = df.copy()
    new_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            new_cols.append("_".join(str(x) for x in c if x) or "col")
        else:
            new_cols.append(str(c))
    df.columns = new_cols

    # Parquet con datetime64 se escribe como INT64 (timestamp); BigQuery DATE espera date32.
    # Convertir 'date' a date para que PyArrow escriba date32[day].
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=False).dt.date

    prefix = date_prefix or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_path = f"raw/{prefix}/stock_prices.parquet"

    try:
        from google.cloud import storage

        client = storage.Client(project=project)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        buf = io.BytesIO()
        df.to_parquet(buf, index=False, engine="pyarrow")
        buf.seek(0)
        blob.upload_from_file(buf, content_type="application/octet-stream")

        uri = f"gs://{bucket_name}/{blob_path}"
        logger.info("Uploaded Parquet to %s", uri)
        return uri
    except Exception as e:
        logger.exception("Failed to upload to GCS: %s", e)
        return None
