"""
Carga de datos a Cloud Storage (GCS) en formato Parquet.
Estructura: bucket/raw/YYYY-MM-DD/stock_prices.parquet
"""
import io
import logging
from datetime import datetime, timezone

import pandas as pd

from src.config import get_gcs_bucket

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
    if not bucket_name:
        logger.error("GCS_BUCKET not set")
        return None

    prefix = date_prefix or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_path = f"raw/{prefix}/stock_prices.parquet"

    try:
        from google.cloud import storage

        client = storage.Client()
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
