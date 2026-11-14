resource "google_iap_tunnel_instance_iam_member" "operator" {
  count    = var.operator_member == null ? 0 : 1
  project  = var.project_id
  zone     = var.zone
  instance = module.compute.name
  role     = "roles/iap.tunnelResourceAccessor"
  member   = var.operator_member
}
resource "google_compute_instance_iam_member" "operator" {
  count         = var.operator_member == null ? 0 : 1
  project       = var.project_id
  zone          = var.zone
  instance_name = module.compute.name
  role          = "roles/compute.osAdminLogin"
  member        = var.operator_member
}
resource "google_service_account_iam_member" "operator" {
  count              = var.operator_member == null ? 0 : 1
  service_account_id = "projects/${var.project_id}/serviceAccounts/${module.iam.vm_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = var.operator_member
}
