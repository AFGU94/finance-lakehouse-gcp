# Financial Data Lakehouse (GCP Free Tier)

Data Lakehouse financiero **serverless** en Google Cloud, diseñado para mantenerse **100% en Free Tier**: ETL con yfinance, Cloud Run Jobs, GCS, BigQuery y dbt.

## Arquitectura (ELT)

```
[Cloud Scheduler 8:00 AM] → [Cloud Run Job]
                                    │
    (1) Extract  ← Python (yfinance) → Yahoo Finance API
    (2) Load     → GCS (raw/YYYY-MM-DD/*.parquet)
    (3) Load     → BigQuery (staging)
    (4) Transform → dbt Core → BigQuery (marts)
```

## Cinturón de seguridad (costes $0)

| Recurso | Límite configurado |
|--------|---------------------|
| **Región** | `us-central1` (obligatorio) |
| **Cloud Run Job** | 512 MiB RAM, 1 CPU, timeout 60 s |
| **Cloud Storage** | Lifecycle: borrar objetos > 30 días (límite gratis 5 GB) |
| **Artifact Registry** | Cleanup: mantener solo las últimas 2 imágenes |

## Prerrequisitos

1. **Cuenta GCP** y un proyecto (o crea uno nuevo).
2. **gcloud** instalado y autenticado:
   ```bash
   gcloud auth application-default login
   gcloud config set project TU_PROJECT_ID
   ```
3. **Terraform** ≥ 1.5.
4. **Docker** (para construir la imagen del job más adelante).

## Uso rápido (Fase 1 – solo infra)

1. **Variables**
   ```bash
   cp infra/terraform.tfvars.example infra/terraform.tfvars
   # Edita infra/terraform.tfvars y pon tu project_id
   ```

2. **Desplegar infraestructura**
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

3. **Región obligatoria**  
   Todo está en `us-central1`. No cambies la región si quieres mantener Free Tier.

## Estructura del proyecto

- **`/infra`** – Terraform (GCS, Artifact Registry, BigQuery, Cloud Run Job, Cloud Scheduler).
- **`/src`** – Scripts Python de ingestión (yfinance → Parquet, carga a BigQuery).
- **`/dbt_project`** – Modelos dbt (staging → marts).

## Fase 2 – Ingestión (src)

Pipeline: **yfinance** → Parquet en GCS `raw/YYYY-MM-DD/` → BigQuery `staging.stock_prices`.

**Ejecutar en local** (desde la raíz del repo, con `.venv` activado):

```bash
# Variables de entorno (mismas que inyecta Terraform en Cloud Run)
export GCS_BUCKET=tu-bucket-name
export BQ_PROJECT=tu-project-id
export BQ_DATASET_STAGING=staging
python -m src.main
```

Tickers por defecto: `AAPL`, `MSFT`, `TSLA` (editar `src/config.py` para cambiar).

**Siguientes pasos (Fase 2.3–2.4):** Dockerfile que ejecute `python -m src.main`, push a Artifact Registry y actualizar la imagen del Cloud Run Job en Terraform.

## Stack

- **Lenguaje:** Python 3.9+
- **IaC:** Terraform
- **Contenedores:** Docker → Cloud Run Jobs
- **Transformación:** dbt Core
- **Control de versiones:** Git
