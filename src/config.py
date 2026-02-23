"""
Configuración del pipeline de ingestión - Financial Data Lakehouse.
Variables de entorno (Cloud Run Job) y constantes.
"""
import os
from typing import List

# Tickers a ingestar (Yahoo Finance)
TICKERS: List[str] = ["AAPL", "MSFT", "TSLA"]

# Nombre de la tabla de staging en BigQuery
STAGING_TABLE_STOCK_PRICES = "stock_prices"

# Variables de entorno (inyectadas por Terraform en Cloud Run Job)
def get_gcs_bucket() -> str:
    return os.environ.get("GCS_BUCKET", "")


def get_bq_project() -> str:
    return os.environ.get("BQ_PROJECT", "")


def get_bq_dataset_staging() -> str:
    return os.environ.get("BQ_DATASET_STAGING", "staging")


def get_bq_dataset_marts() -> str:
    return os.environ.get("BQ_DATASET_MARTS", "marts")
