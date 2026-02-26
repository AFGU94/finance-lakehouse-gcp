# dbt – Financial Lakehouse (marts)

Transforms `staging.stock_prices` into deduplicated tables in `marts`.

## Setup

1. **Install dbt-bigquery** (in the repo root or a venv):
   ```bash
   pip install dbt-bigquery
   ```

2. **Set the project** (same as the ingestion pipeline):
   ```bash
   export BQ_PROJECT=your-project-id
   ```

3. **Authenticate** (if not already):
   ```bash
   gcloud auth application-default login
   ```

## Run

From the **`dbt_project`** directory:

```bash
cd dbt_project
dbt deps   # install packages (none required by default)
dbt run    # build marts.stock_prices
```

To run and run tests:

```bash
dbt run
dbt test
```

## Models

| Model           | Source                    | Description                          |
|----------------|---------------------------|--------------------------------------|
| `marts.stock_prices` | `staging.stock_prices` | One row per (date, symbol); deduplicated. |

## Optional: run after ingest in Cloud Run

You can add a second step in the Job container to run `dbt run` after `python -m src.main`, or run dbt in a separate scheduled Job.
