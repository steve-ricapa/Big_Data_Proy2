variable "prefix" { type = string }
variable "region" { type = string }
variable "cidr" { type = string }
variable "public_https" {
  type    = bool
  default = false
}
resource "google_compute_network" "main" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
}
resource "google_compute_subnetwork" "main" {
  name                     = "${var.prefix}-subnet"
  region                   = var.region
  network                  = google_compute_network.main.id
  ip_cidr_range            = var.cidr
  private_ip_google_access = true
}
resource "google_compute_firewall" "iap" {
  name          = "${var.prefix}-iap-ssh"
  network       = google_compute_network.main.id
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["${var.prefix}-data"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
# Solo Cloud Run Direct VPC egress (network tag). TLS obligatorio en los motores.
resource "google_compute_firewall" "database" {
  name        = "${var.prefix}-web-to-data"
  network     = google_compute_network.main.id
  source_tags = ["${var.prefix}-web"]
  target_tags = ["${var.prefix}-data"]
  allow {
    protocol = "tcp"
    ports    = ["27017", "9042", "7687"]
  }
}
output "network_id" { value = google_compute_network.main.id }
output "subnet_id" { value = google_compute_subnetwork.main.id }
resource "google_compute_firewall" "https" {
  count         = var.public_https ? 1 : 0
  name          = "${var.prefix}-https"
  network       = google_compute_network.main.id
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.prefix}-data"]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}
