variable "project_id" { type = string }
variable "prefix" { type = string }
variable "region" { type = string }
variable "reader" { type = string }
variable "writer" { type = string }
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.prefix}-images"
  format        = "DOCKER"
}
resource "google_artifact_registry_repository_iam_member" "reader" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${var.reader}"
}
# Publish durable app images from the VM; scoped to this repository only.
resource "google_artifact_registry_repository_iam_member" "writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${var.writer}"
}
output "id" { value = google_artifact_registry_repository.images.id }
