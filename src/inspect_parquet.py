import duckdb

FILE_PATH = "2026-02-23/stock_prices.parquet"

con = duckdb.connect()

print("Schema:")
print(con.execute(f"DESCRIBE SELECT * FROM '{FILE_PATH}'").fetchdf())

print("\nSample rows:")
print(con.execute(f"SELECT * FROM '{FILE_PATH}' LIMIT 5").fetchdf())

print("\nRow count:")
print(con.execute(f"SELECT COUNT(*) FROM '{FILE_PATH}'").fetchall())