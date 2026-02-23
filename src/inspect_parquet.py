"""
Inspección rápida de un Parquet (local o tras descargar de GCS).
Usa solo pandas/pyarrow (ya en el proyecto), sin dependencias extra.
"""
import sys
import pandas as pd

# Ruta por defecto: Parquet local (ej. descargado de gs://bucket/raw/YYYY-MM-DD/stock_prices.parquet)
FILE_PATH = sys.argv[1] if len(sys.argv) > 1 else "2026-02-23/stock_prices.parquet"

df = pd.read_parquet(FILE_PATH, engine="pyarrow")

print("Schema:")
print(df.dtypes)
print("\nShape:", df.shape)
print("\nSample (first 5 rows):")
print(df.head())
print("\nRow count:", len(df))
