variable "project_id" { type = string }
variable "prefix" { type = string }
resource "google_service_account" "vm" {
  account_id   = "${var.prefix}-data"
  display_name = "VM datos y Airflow"
}
resource "google_service_account" "web" {
  for_each   = toset(["api", "mcp", "dashboard"])
  account_id = "${var.prefix}-${each.key}"
}
resource "google_project_iam_member" "telemetry" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.vm.email}"
}
output "vm_email" { value = google_service_account.vm.email }
output "web_emails" { value = { for k, s in google_service_account.web : k => s.email } }
