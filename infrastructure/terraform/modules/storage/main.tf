variable "project_id" { type = string }
variable "prefix" { type = string }
variable "region" { type = string }
variable "vm_identity" { type = string }
resource "google_storage_bucket" "data" {
  for_each                    = toset(["raw", "processed"])
  name                        = "${var.project_id}-${var.prefix}-${each.key}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  soft_delete_policy { retention_duration_seconds = 604800 }
  dynamic "lifecycle_rule" {
    for_each = each.key == "processed" ? [1] : []
    content {
      condition {
        age            = 7
        matches_prefix = ["backups/"]
      }
      action { type = "Delete" }
    }
  }
}
resource "google_storage_bucket_iam_member" "vm" {
  for_each = google_storage_bucket.data
  bucket   = each.value.name
  role     = each.key == "raw" ? "roles/storage.objectViewer" : "roles/storage.objectUser"
  member   = "serviceAccount:${var.vm_identity}"
}
output "names" { value = { for k, b in google_storage_bucket.data : k => b.name } }
