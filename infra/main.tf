# ------------------------------------------------------------------------------
# Financial Data Lakehouse - Infraestructura principal
# Guardrails: us-central1, límites Cloud Run, lifecycle GCS, cleanup Artifact Registry
# ------------------------------------------------------------------------------

locals {
  bucket_name = "${var.bucket_name_prefix}-${var.project_id}"
}

# ----- Service Account para Cloud Run Job (mínimos permisos) -----
resource "google_service_account" "lakehouse_job" {
  account_id   = "finance-lakehouse-job"
  display_name = "Financial Lakehouse - Cloud Run Job"
  project      = var.project_id
}

resource "google_project_iam_member" "job_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.lakehouse_job.email}"
}

resource "google_project_iam_member" "job_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.lakehouse_job.email}"
}

resource "google_project_iam_member" "job_bigquery_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.lakehouse_job.email}"
}

# ----- Cloud Storage (Data Lake) + Lifecycle 30 días -----
resource "google_storage_bucket" "lakehouse" {
  name     = local.bucket_name
  location = var.region
  project  = var.project_id

  # Free Tier: mantener por debajo de 5GB
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true
}

# ----- Artifact Registry (Docker) + mantener solo 2 imágenes -----
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
  project       = var.project_id
  description   = "Imágenes Docker para Financial Lakehouse (Cloud Run Job)"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-latest-2"
    action = "KEEP"
    most_recent_versions {
      keep_count = 2
    }
  }
}

# ----- BigQuery dataset (staging + marts) -----
resource "google_bigquery_dataset" "staging" {
  dataset_id = "staging"
  location   = var.region
  project    = var.project_id
  description = "Datos crudos cargados desde GCS (ELT staging)"
}

resource "google_bigquery_dataset" "marts" {
  dataset_id = "marts"
  location   = var.region
  project    = var.project_id
  description = "Tablas finales transformadas por dbt"
}

# ----- Cloud Run Job (límites duros Free Tier) -----
# Imagen: placeholder hasta que tengas la imagen en Artifact Registry.
# Tras el primer `docker build` y `push`, usa la imagen real.
resource "google_cloud_run_v2_job" "ingest" {
  name     = var.cloud_run_job_name
  location = var.region
  project  = var.project_id

  template {
    template {
      max_retries = 1
      timeout     = "60s" # Límite duro: 60 segundos

      containers {
        image = "us-docker.pkg.dev/cloudrun/container/job:latest" # Placeholder; reemplazar por tu imagen

        resources {
          limits = {
            "cpu"    = "1"
            "memory" = "512Mi"
          }
        }

        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.lakehouse.name
        }
        env {
          name  = "BQ_PROJECT"
          value = var.project_id
        }
        env {
          name  = "BQ_DATASET_STAGING"
          value = google_bigquery_dataset.staging.dataset_id
        }
        env {
          name  = "BQ_DATASET_MARTS"
          value = google_bigquery_dataset.marts.dataset_id
        }
      }

      service_account = google_service_account.lakehouse_job.email
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image
    ]
  }
}

# ----- Cloud Scheduler: dispara el Job a las 8:00 AM -----
resource "google_cloud_scheduler_job" "ingest_daily" {
  name        = "finance-ingest-daily"
  description = "Trigger diario 8:00 AM - Financial Lakehouse ingest job"
  schedule    = var.scheduler_cron
  time_zone   = "America/New_York"
  region      = var.region
  project     = var.project_id

  http_target {
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.ingest.name}:run"
    http_method = "POST"
    oauth_token {
      service_account_email = google_service_account.lakehouse_job.email
    }
  }
}

# ----- Permiso para que la SA del Job pueda invocarse (Scheduler usa OAuth con esta SA) -----
resource "google_cloud_run_v2_job_iam_member" "job_self_invoker" {
  location = google_cloud_run_v2_job.ingest.location
  name     = google_cloud_run_v2_job.ingest.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.lakehouse_job.email}"
}
