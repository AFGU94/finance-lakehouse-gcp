# ------------------------------------------------------------------------------
# Variables - Región obligatoria us-central1 (Free Tier)
# ------------------------------------------------------------------------------

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region. OBLIGATORIO us-central1 para Always Free Tier."
  type        = string
  default     = "us-central1"
}

variable "scheduler_cron" {
  description = "Cron para Cloud Scheduler (ej: 8:00 AM = 0 8 * * *)"
  type        = string
  default     = "0 8 * * *"
}

variable "cloud_run_job_name" {
  description = "Nombre del Cloud Run Job (ingestión + dbt)"
  type        = string
  default     = "finance-ingest-job"
}

variable "bucket_name_prefix" {
  description = "Prefijo del bucket GCS (se añade project_id para unicidad)"
  type        = string
  default     = "finance-lakehouse"
}

variable "artifact_registry_repo" {
  description = "Nombre del repositorio en Artifact Registry para imágenes Docker"
  type        = string
  default     = "finance-lakehouse"
}

variable "ingest_image" {
  description = "Imagen Docker del pipeline de ingestión (Artifact Registry). Si no se define, se usa REPO/ingest:latest."
  type        = string
  default     = ""
}
