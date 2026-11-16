variable "project_id" { type = string }
variable "prefix" { type = string }
variable "vm_identity" { type = string }
# Solo contenedores de secretos. Nunca secret_version/secret_data en Terraform.
resource "google_secret_manager_secret" "main" {
  for_each  = toset(["mongodb-uri", "mongodb-root-password", "cassandra-password", "neo4j-password", "postgres-password", "airflow-db-uri", "airflow-fernet-key", "airflow-web-key", "mcp-token", "runtime-bootstrap"])
  project   = var.project_id
  secret_id = "${var.prefix}-${each.key}"
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_iam_member" "vm" {
  for_each  = { for k, s in google_secret_manager_secret.main : k => s if k != "mcp-token" }
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.vm_identity}"
}
output "ids" { value = { for k, s in google_secret_manager_secret.main : k => s.secret_id } }
