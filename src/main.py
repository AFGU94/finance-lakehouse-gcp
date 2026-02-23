"""
Entrypoint del pipeline de ingestión - Financial Data Lakehouse.
Extract (yfinance) -> Load GCS (Parquet) -> Load BigQuery (staging).
Ejecutar: python -m src.main o desde src/: python main.py
"""
import logging
import sys
from datetime import datetime, timezone

from src.config import get_bq_dataset_staging, get_gcs_bucket
from src.extract import extract_stock_data
from src.load_bigquery import load_to_bigquery
from src.load_gcs import save_to_gcs

# Cloud Logging captura stdout/stderr en Cloud Run; configurar nivel INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_ingestion(period: str = "1mo") -> int:
    """
    Ejecuta el pipeline: extraer -> GCS -> BigQuery.

    Returns:
        0 si todo ok, 1 si hubo error.
    """
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("Starting ingestion for date_prefix=%s, period=%s", date_prefix, period)

    if not get_gcs_bucket():
        logger.error("GCS_BUCKET not set; set env or run with GCS_BUCKET=...")
        return 1

    df = extract_stock_data(period=period)
    if df is None or df.empty:
        logger.error("No data extracted")
        return 1

    logger.info("Extracted %d rows", len(df))

    gcs_uri = save_to_gcs(df, date_prefix=date_prefix)
    if not gcs_uri:
        logger.error("Failed to upload to GCS")
        return 1

    if not load_to_bigquery(gcs_uri=gcs_uri):
        logger.error("Failed to load to BigQuery")
        return 1

    logger.info("Ingestion completed: %s -> %s.%s", gcs_uri, get_bq_dataset_staging(), "stock_prices")
    return 0


if __name__ == "__main__":
    sys.exit(run_ingestion())
