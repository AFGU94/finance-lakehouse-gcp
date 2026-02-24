"""
Entrypoint del pipeline de ingestión - Financial Data Lakehouse.
Extract (yfinance) -> Load GCS (Parquet) -> Load BigQuery (staging).

Uso:
  Carga incremental (2 días, uso diario):  python -m src.main
  Carga inicial / backfill (1 mes):         python -m src.main --backfill
"""
import argparse
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


def run_ingestion(incremental: bool = True, backfill_period: str = "1mo") -> int:
    """
    Ejecuta el pipeline: extraer -> GCS -> BigQuery.

    Args:
        incremental: True = ventana 2 días (uso diario). False = backfill con period.
        backfill_period: Solo si incremental=False. Ej: 1mo, 3mo, 6mo, 1y.

    Returns:
        0 si todo ok, 1 si hubo error.
    """
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mode = "incremental (2d)" if incremental else f"backfill ({backfill_period})"
    logger.info("Starting ingestion for date_prefix=%s, mode=%s", date_prefix, mode)

    if not get_gcs_bucket():
        logger.error("GCS_BUCKET not set; set env or run with GCS_BUCKET=...")
        return 1

    df = extract_stock_data(incremental=incremental, period=backfill_period if not incremental else None)
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Financial Lakehouse: ingestión yfinance -> GCS -> BigQuery.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  Carga inicial (1 mes, una vez):   python -m src.main --backfill
  Carga incremental (2 días):     python -m src.main
  Backfill 3 meses:                python -m src.main --backfill --period 3mo
        """,
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Carga inicial / backfill con ventana de tiempo (default: 1mo).",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        help="Ventana para backfill si --backfill (default: 1mo). Ej: 1mo, 3mo, 6mo, 1y.",
    )
    args = parser.parse_args()
    return run_ingestion(incremental=not args.backfill, backfill_period=args.period)


if __name__ == "__main__":
    sys.exit(main())
