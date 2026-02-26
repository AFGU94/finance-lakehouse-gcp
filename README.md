# Financial Data Lakehouse (GCP Free Tier)

**This document is also available in [Spanish](README.es.md).**

A **serverless** financial Data Lakehouse on Google Cloud, designed to stay **100% within the Free Tier**: ingestion with yfinance, Cloud Run Jobs, GCS, BigQuery, and (optionally) dbt.

---

## Architecture (ELT)

```
[Cloud Scheduler 8:00 AM] → [Cloud Run Job]
                                    │
    (1) Extract  ← Python (yfinance) → Yahoo Finance API
    (2) Load     → GCS (raw/YYYY-MM-DD/*.parquet)
    (3) Load     → BigQuery (staging.stock_prices)
    (4) Transform → dbt Core → BigQuery (marts)  [pending]
```

---

## Cost guardrails ($0 target)

| Resource | Configured limit |
|----------|------------------|
| **Region** | `us-central1` (required) |
| **Cloud Run Job** | 512 MiB RAM, 1 CPU, 60 s timeout |
| **Cloud Storage** | Lifecycle: delete objects older than 30 days (5 GB free limit) |
| **Artifact Registry** | Cleanup: keep only the latest 2 images |

---

## Project structure

| Folder / file | Contents |
|---------------|----------|
| **`/infra`** | Terraform: GCS, Artifact Registry, BigQuery (staging + marts), Cloud Run Job, Cloud Scheduler, Service Account. |
| **`/src`** | Python pipeline: `config.py` (tickers, env), `extract.py` (yfinance), `load_gcs.py`, `load_bigquery.py`, `main.py` (entrypoint). |
| **`/dbt_project`** | dbt models (staging → marts), to be implemented. |

---

## Prerequisites

- **GCP account** and a project.
- **gcloud** installed and authenticated.
- **Terraform** ≥ 1.5 (HashiCorp official repository recommended).
- **Docker** (to build and push the Job image).
- **Python 3.9+** and a `.venv` in the repo root to run the pipeline locally.

---

## Step-by-step execution

Recommended order to get the project running end-to-end.

### 0. Authentication and APIs (once per project)

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Enable required APIs (replace `YOUR_PROJECT_ID`):

```bash
for api in run.googleapis.com cloudscheduler.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com storage.googleapis.com iam.googleapis.com; do
  gcloud services enable $api --project=YOUR_PROJECT_ID
done
```

---

### Phase 1 – Infrastructure (Terraform)

1. **Variables**
   ```bash
   cp infra/terraform.tfvars.example infra/terraform.tfvars
   # Edit infra/terraform.tfvars and set project_id
   ```

2. **Deploy**
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```
   Everything deploys in `us-central1`. Do not change the region to stay within Free Tier.

3. **Note the outputs** (bucket, image URL for Docker):
   ```bash
   cd infra
   terraform output gcs_bucket
   terraform output ingest_image
   ```
   If `ingest_image` is not available, use: `us-central1-docker.pkg.dev/YOUR_PROJECT_ID/finance-lakehouse/ingest:latest`.

---

### Phase 2.1 + 2.2 – Ingestion pipeline (local)

The pipeline uses **incremental load** by default (last 2 days). Use `--backfill` for the **initial load**.

**Environment variables** (same as those Terraform injects into Cloud Run):

```bash
export GCS_BUCKET=finance-lakehouse-YOUR_PROJECT_ID   # or: terraform -C infra output -raw gcs_bucket
export BQ_PROJECT=YOUR_PROJECT_ID
export BQ_DATASET_STAGING=staging
```

**Initial load (once, ~1 month of data):**
```bash
cd ~/proyectos/finance-lakehouse-gcp
source .venv/bin/activate
pip install -r src/requirements.txt   # if needed
python -m src.main --backfill
```

**Incremental load (2 days, daily use):**
```bash
python -m src.main
```

**Other options:**
```bash
python -m src.main --help
python -m src.main --backfill --period 3mo   # 3-month backfill
```

**Tickers:** configured by default in `src/config.py` (e.g. AMZN). Edit that list to change them.

**Verify in BigQuery:**
- Range and total: `SELECT MIN(date), MAX(date), COUNT(*) FROM \`YOUR_PROJECT.staging.stock_prices\`;`
- Duplicates (after several incremental runs):  
  `SELECT date, symbol, COUNT(*) FROM \`YOUR_PROJECT.staging.stock_prices\` GROUP BY 1,2 HAVING COUNT(*)>1;`  
  Those duplicates are cleaned in the marts layer (dbt).

---

### Phase 2.3 – Docker image

Build and test locally (mount credentials for GCS/BigQuery):

```bash
docker build -t finance-ingest .
docker run --rm \
  -v ~/.config/gcloud:/root/.config/gcloud \
  -e GCS_BUCKET=finance-lakehouse-YOUR_PROJECT_ID \
  -e BQ_PROJECT=YOUR_PROJECT_ID \
  -e BQ_DATASET_STAGING=staging \
  finance-ingest
```

On Cloud Run you do not need to mount credentials; the Job uses the Terraform Service Account.

---

### Phase 2.4 – Push to Artifact Registry and update the Job

1. **Configure Docker for Artifact Registry** (once):
   ```bash
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

2. **Build and push the image** (use the URL from `terraform output ingest_image` or the one below):
   ```bash
   docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/finance-lakehouse/ingest:latest .
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/finance-lakehouse/ingest:latest
   ```

3. **Update the Job** (Terraform already points to this image):
   ```bash
   cd infra && terraform apply
   ```

4. **Test the Job in GCP** (optional):
   ```bash
   gcloud run jobs execute finance-ingest-job --region us-central1 --project YOUR_PROJECT_ID
   ```
   The Scheduler runs it daily at 8:00 AM.

**After changing code (e.g. tickers or logic):** run `docker build` and `docker push` again with the same tag; the next Job execution will use the new image.

---

### Phase 2.5 – dbt

Models in `/dbt_project` read from `staging.stock_prices`, deduplicate by `(date, symbol)`, and write to `marts.stock_prices`.

1. **Install dbt-bigquery** (e.g. in repo venv): `pip install dbt-bigquery`
2. **From the `dbt_project` directory:**
   ```bash
   export BQ_PROJECT=YOUR_PROJECT_ID
   cd dbt_project
   dbt deps
   dbt run
   ```
3. **Optional:** run dbt after ingest in the same Cloud Run Job (add `dbt run` to the container entrypoint) or in a separate scheduled Job.

See `dbt_project/README.md` for details.

---

## Useful commands summary

| Action | Command |
|--------|---------|
| Initial load (1 month) | `python -m src.main --backfill` |
| Incremental load (2d) | `python -m src.main` |
| Pipeline help | `python -m src.main --help` |
| Build + push image | `docker build -t ... ; docker push ...` |
| Execute Job in GCP | `gcloud run jobs execute finance-ingest-job --region us-central1 --project YOUR_PROJECT_ID` |
| Run dbt (marts) | `cd dbt_project && dbt run` (set `BQ_PROJECT` first) |

---

## Stack

- **Language:** Python 3.9+
- **IaC:** Terraform
- **Containers:** Docker → Cloud Run Jobs
- **Transform:** dbt Core (optional)
- **Version control:** Git
