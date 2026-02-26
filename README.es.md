# Financial Data Lakehouse (GCP Free Tier)

Data Lakehouse financiero **serverless** en Google Cloud, diseñado para mantenerse **100% en Free Tier**: ingestión con yfinance, Cloud Run Jobs, GCS, BigQuery y (opcional) dbt.

---

## Arquitectura (ELT)

```
[Cloud Scheduler 8:00 AM] → [Cloud Run Job]
                                    │
    (1) Extract  ← Python (yfinance) → Yahoo Finance API
    (2) Load     → GCS (raw/YYYY-MM-DD/*.parquet)
    (3) Load     → BigQuery (staging.stock_prices)
    (4) Transform → dbt Core → BigQuery (marts)  [pendiente]
```

---

## Cinturón de seguridad (costes $0)

| Recurso | Límite configurado |
|--------|---------------------|
| **Región** | `us-central1` (obligatorio) |
| **Cloud Run Job** | 512 MiB RAM, 1 CPU, timeout 60 s |
| **Cloud Storage** | Lifecycle: borrar objetos > 30 días (límite gratis 5 GB) |
| **Artifact Registry** | Cleanup: mantener solo las últimas 2 imágenes |

---

## Estructura del proyecto

| Carpeta / archivo | Contenido |
|-------------------|-----------|
| **`/infra`** | Terraform: GCS, Artifact Registry, BigQuery (staging + marts), Cloud Run Job, Cloud Scheduler, Service Account. |
| **`/src`** | Pipeline Python: `config.py` (tickers, env), `extract.py` (yfinance), `load_gcs.py`, `load_bigquery.py`, `main.py` (entrypoint). |
| **`/dbt_project`** | Modelos dbt (staging → marts), pendiente de implementar. |

---

## Prerrequisitos

- **Cuenta GCP** y un proyecto.
- **gcloud** instalado y autenticado.
- **Terraform** ≥ 1.5 (repositorio oficial HashiCorp recomendado).
- **Docker** (para construir y subir la imagen del Job).
- **Python 3.9+** y `.venv` en la raíz para ejecutar el pipeline en local.

---

## Paso a paso de ejecución

Orden recomendado para dejar el proyecto funcionando de punta a punta.

### 0. Autenticación y APIs (una vez por proyecto)

```bash
gcloud auth application-default login
gcloud config set project TU_PROJECT_ID
```

Activar APIs necesarias (sustituir `TU_PROJECT_ID`):

```bash
for api in run.googleapis.com cloudscheduler.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com storage.googleapis.com iam.googleapis.com; do
  gcloud services enable $api --project=TU_PROJECT_ID
done
```

---

### Fase 1 – Infraestructura (Terraform)

1. **Variables**
   ```bash
   cp infra/terraform.tfvars.example infra/terraform.tfvars
   # Editar infra/terraform.tfvars y poner project_id
   ```

2. **Desplegar**
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```
   Todo se despliega en `us-central1`. No cambiar la región para mantener Free Tier.

3. **Anotar outputs** (bucket, imagen para Docker):
   ```bash
   terraform output gcs_bucket
   terraform output ingest_image
   ```
   Si `ingest_image` no aparece, usar: `us-central1-docker.pkg.dev/TU_PROJECT_ID/finance-lakehouse/ingest:latest`.

---

### Fase 2.1 + 2.2 – Pipeline de ingestión (local)

El pipeline hace **carga incremental** por defecto (últimos 2 días). Para **carga inicial** (backfill) se usa `--backfill`.

**Variables de entorno** (mismas que inyecta Terraform en Cloud Run):

```bash
export GCS_BUCKET=finance-lakehouse-TU_PROJECT_ID   # o: terraform -C infra output -raw gcs_bucket
export BQ_PROJECT=TU_PROJECT_ID
export BQ_DATASET_STAGING=staging
```

**Carga inicial (una vez, ~1 mes de datos):**
```bash
cd ~/proyectos/finance-lakehouse-gcp
source .venv/bin/activate
pip install -r src/requirements.txt   # si hace falta
python -m src.main --backfill
```

**Carga incremental (2 días, uso diario):**
```bash
python -m src.main
```

**Otras opciones:**
```bash
python -m src.main --help
python -m src.main --backfill --period 3mo   # backfill de 3 meses
```

**Tickers:** por defecto en `src/config.py` (ej. AMZN). Editar esa lista para cambiar.

**Comprobar en BigQuery:**
- Rango y total: `SELECT MIN(date), MAX(date), COUNT(*) FROM \`TU_PROJECT.staging.stock_prices\`;`
- Duplicados (tras varias cargas incrementales):  
  `SELECT date, symbol, COUNT(*) FROM \`TU_PROJECT.staging.stock_prices\` GROUP BY 1,2 HAVING COUNT(*)>1;`  
  Esos duplicados se limpian en la capa marts (dbt).

---

### Fase 2.3 – Imagen Docker

Construir y probar en local (credenciales montadas para GCS/BigQuery):

```bash
docker build -t finance-ingest .
docker run --rm \
  -v ~/.config/gcloud:/root/.config/gcloud \
  -e GCS_BUCKET=finance-lakehouse-TU_PROJECT_ID \
  -e BQ_PROJECT=TU_PROJECT_ID \
  -e BQ_DATASET_STAGING=staging \
  finance-ingest
```

En Cloud Run no hace falta montar credenciales; el Job usa la Service Account de Terraform.

---

### Fase 2.4 – Push a Artifact Registry y actualizar el Job

1. **Configurar Docker para Artifact Registry** (una vez):
   ```bash
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

2. **Construir y subir la imagen** (usar la URL de `terraform output ingest_image` o la de abajo):
   ```bash
   docker build -t us-central1-docker.pkg.dev/TU_PROJECT_ID/finance-lakehouse/ingest:latest .
   docker push us-central1-docker.pkg.dev/TU_PROJECT_ID/finance-lakehouse/ingest:latest
   ```

3. **Actualizar el Job** (ya apunta a esa imagen en Terraform):
   ```bash
   cd infra && terraform apply
   ```

4. **Probar el Job en GCP** (opcional):
   ```bash
   gcloud run jobs execute finance-ingest-job --region us-central1 --project TU_PROJECT_ID
   ```
   El Scheduler lo ejecuta cada día a las 8:00 AM.

**Después de cambiar código (p. ej. tickers o lógica):** volver a hacer `docker build`, `docker push` con el mismo tag; la siguiente ejecución del Job usará la nueva imagen.

---

### Fase 2.5 – dbt (pendiente)

- **Objetivo:** modelos en `/dbt_project` que lean de `staging.stock_prices`, dedupliquen por `(date, symbol)` y escriban en `marts`.
- **Ejecución:** se puede integrar dbt en el mismo contenedor del Job (después de `python -m src.main`) o en un Job aparte.

---

## Resumen de comandos útiles

| Acción | Comando |
|--------|--------|
| Carga inicial 1 mes | `python -m src.main --backfill` |
| Carga incremental 2d | `python -m src.main` |
| Ayuda del pipeline | `python -m src.main --help` |
| Build + push imagen | `docker build -t ... ; docker push ...` |
| Ejecutar Job en GCP | `gcloud run jobs execute finance-ingest-job --region us-central1 --project TU_PROJECT_ID` |

---

## Stack

- **Lenguaje:** Python 3.9+
- **IaC:** Terraform
- **Contenedores:** Docker → Cloud Run Jobs
- **Transformación:** dbt Core (opcional)
- **Control de versiones:** Git
