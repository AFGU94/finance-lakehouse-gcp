# ------------------------------------------------------------------------------
# Terraform & Provider versions - Financial Data Lakehouse (GCP Free Tier)
# ------------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Backend: local por defecto. Para equipo/producción, usar GCS:
  # backend "gcs" { bucket = "tf-state-XXX" prefix = "lakehouse" }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
