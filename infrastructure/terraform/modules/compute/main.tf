variable "prefix" { type = string }
variable "zone" { type = string }
variable "machine_type" { type = string }
variable "boot_image" { type = string }
variable "boot_disk_gb" { type = number }
variable "data_disk_gb" { type = number }
variable "disk_type" { type = string }
variable "subnet" { type = string }
variable "service_account" { type = string }
variable "external_ip" { type = bool }
variable "reserved_external_address" {
  type    = string
  default = null
}
variable "protect" { type = bool }
variable "startup_script" { type = string }
resource "google_compute_disk" "data" {
  name = "${var.prefix}-data"
  zone = var.zone
  type = var.disk_type
  size = var.data_disk_gb
  lifecycle { prevent_destroy = true }
}
resource "google_compute_disk" "boot" {
  name  = "${var.prefix}-boot"
  zone  = var.zone
  type  = var.disk_type
  size  = var.boot_disk_gb
  image = var.boot_image
  lifecycle { prevent_destroy = true }
}
resource "google_compute_address" "public" {
  count        = var.external_ip && var.reserved_external_address != null ? 1 : 0
  name         = "${var.prefix}-public"
  region       = join("-", slice(split("-", var.zone), 0, 2))
  address      = var.reserved_external_address
  network_tier = "PREMIUM"
}
resource "google_compute_instance" "main" {
  name                      = "${var.prefix}-data"
  zone                      = var.zone
  machine_type              = var.machine_type
  allow_stopping_for_update = true
  deletion_protection       = var.protect
  tags                      = ["${var.prefix}-data"]
  boot_disk {
    source      = google_compute_disk.boot.id
    auto_delete = false
    device_name = "ti-boot"
  }
  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "ti-data"
  }
  network_interface {
    subnetwork = var.subnet
    dynamic "access_config" {
      for_each = var.external_ip ? [1] : []
      content {
        nat_ip = var.reserved_external_address != null ? google_compute_address.public[0].address : null
      }
    }
  }
  metadata = {
    enable-oslogin           = "TRUE"
    block-project-ssh-keys   = "TRUE"
    disable-legacy-endpoints = "TRUE"
  }
  metadata_startup_script = var.startup_script
  service_account {
    email  = var.service_account
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
}
output "name" { value = google_compute_instance.main.name }
output "private_ip" { value = google_compute_instance.main.network_interface[0].network_ip }
output "disk_name" { value = google_compute_disk.data.name }
