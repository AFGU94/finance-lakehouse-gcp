"""
Carga de datos desde GCS a BigQuery (tabla de staging).
Crea la tabla si no existe y carga el Parquet.
"""
import logging
from typing import Optional

from google.cloud import bigquery

from src.config import (
    STAGING_TABLE_STOCK_PRICES,
    get_bq_dataset_staging,
    get_bq_project,
    get_gcs_bucket,
)

logger = logging.getLogger(__name__)

# Schema para staging.stock_prices (compatible con Parquet de yfinance)
STOCK_PRICES_SCHEMA = [
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("symbol", "STRING"),
    bigquery.SchemaField("open", "FLOAT64"),
    bigquery.SchemaField("high", "FLOAT64"),
    bigquery.SchemaField("low", "FLOAT64"),
    bigquery.SchemaField("close", "FLOAT64"),
    bigquery.SchemaField("adj_close", "FLOAT64"),
    bigquery.SchemaField("volume", "INT64"),
]


def load_to_bigquery(gcs_uri: Optional[str] = None, date_prefix: Optional[str] = None) -> bool:
    """
    Carga el Parquet de GCS a BigQuery staging.

    Args:
        gcs_uri: URI gs://bucket/raw/YYYY-MM-DD/stock_prices.parquet.
                 Si None, se construye con bucket y date_prefix.
        date_prefix: YYYY-MM-DD para construir la URI si gcs_uri es None.

    Returns:
        True si la carga tuvo éxito.
    """
    project = get_bq_project()
    dataset_id = get_bq_dataset_staging()
    bucket_name = get_gcs_bucket()

    if not project or not dataset_id:
        logger.error("BQ_PROJECT or BQ_DATASET_STAGING not set")
        return False

    if not gcs_uri and bucket_name and date_prefix:
        gcs_uri = f"gs://{bucket_name}/raw/{date_prefix}/stock_prices.parquet"
    if not gcs_uri:
        logger.error("No GCS URI provided and cannot build one")
        return False

    try:
        client = bigquery.Client(project=project)
        table_id = f"{project}.{dataset_id}.{STAGING_TABLE_STOCK_PRICES}"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            schema=STOCK_PRICES_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
        load_job.result()

        logger.info("Loaded %s into %s", gcs_uri, table_id)
        return True
    except Exception as e:
        logger.exception("BigQuery load failed: %s", e)
        return False
