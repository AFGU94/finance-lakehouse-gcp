# ------------------------------------------------------------------------------
# Outputs - Financial Data Lakehouse
# ------------------------------------------------------------------------------

output "project_id" {
  description = "GCP Project ID (BQ_PROJECT para dbt y pipeline)"
  value       = var.project_id
}

output "gcs_bucket" {
  description = "Bucket GCS del Data Lake (raw Parquet)"
  value       = google_storage_bucket.lakehouse.name
}

output "artifact_registry_repository" {
  description = "Repositorio Artifact Registry para imágenes Docker"
  value       = google_artifact_registry_repository.docker.name
}

output "artifact_registry_url" {
  #description = "URL para docker push (sin imagen)"
  description = "URL base para docker push (sin imagen:tag)"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}

output "ingest_image" {
  description = "Imagen que usa el Cloud Run Job (tag para docker push)"
  value       = local.ingest_image
}

output "bigquery_staging_dataset" {
  description = "Dataset BigQuery staging"
  value       = google_bigquery_dataset.staging.dataset_id
}

output "bigquery_marts_dataset" {
  description = "Dataset BigQuery marts (dbt)"
  value       = google_bigquery_dataset.marts.dataset_id
}

output "cloud_run_job_name" {
  description = "Nombre del Cloud Run Job"
  value       = google_cloud_run_v2_job.ingest.name
}

output "cloud_scheduler_job" {
  description = "Nombre del Cloud Scheduler job (8:00 AM)"
  value       = google_cloud_scheduler_job.ingest_daily.name
}

output "service_account_email" {
  description = "Service Account del Cloud Run Job"
  value       = google_service_account.lakehouse_job.email
}
