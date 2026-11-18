terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.49.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

variable "project_id" {
  type    = string
  default = "proyectobigdata2-514216"
}

variable "primary_ip" {
  type    = string
  default = "10.42.0.2"
}

locals {
  # Do not import or manage the existing VM from this state.
  nodes = {
    ti-cassandra-02 = { zone = "us-central1-b", ip = "10.42.0.12" }
    ti-cassandra-03 = { zone = "us-central1-c", ip = "10.42.0.13" }
  }
  vpc = "projects/${var.project_id}/global/networks/ti-dev-vpc"
  ips = concat([var.primary_ip], [for node in local.nodes : node.ip])
}

resource "google_compute_address" "peer" {
  for_each     = local.nodes
  name         = each.key
  address_type = "INTERNAL"
  address      = each.value.ip
  subnetwork   = "ti-dev-subnet"
}

resource "google_compute_disk" "peer" {
  for_each = local.nodes
  name     = "${each.key}-data"
  zone     = each.value.zone
  size     = 20
  type     = "pd-balanced"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_instance" "peer" {
  for_each            = local.nodes
  name                = each.key
  zone                = each.value.zone
  machine_type        = "e2-standard-2"
  deletion_protection = true
  tags                = ["ti-cassandra-peer"]

  boot_disk {
    auto_delete = false
    initialize_params {
      image = "projects/cos-cloud/global/images/cos-stable-121-18867-652-66"
      size  = 20
      type  = "pd-standard"
    }
  }
  attached_disk {
    source      = google_compute_disk.peer[each.key].id
    device_name = "ti-cassandra-data"
  }
  network_interface {
    subnetwork = "ti-dev-subnet"
    network_ip = google_compute_address.peer[each.key].address
  }
  # No external IP or guest service account. The pinned image is loaded over IAP.
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    startup-script         = file("${path.module}/../../../scripts/cassandra-peer-startup.sh")
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
}

resource "google_compute_firewall" "peer_iap" {
  name          = "ti-cassandra-iap"
  network       = local.vpc
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["ti-cassandra-peer"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_firewall" "internode" {
  name               = "ti-cassandra-internode"
  network            = local.vpc
  source_ranges      = [for ip in local.ips : "${ip}/32"]
  destination_ranges = [for ip in local.ips : "${ip}/32"]
  target_tags        = ["ti-cassandra-peer", "ti-dev-data"]

  allow {
    protocol = "tcp"
    ports    = ["7000"]
  }
}

resource "google_compute_firewall" "cql" {
  name          = "ti-cassandra-cql"
  network       = local.vpc
  source_ranges = ["${var.primary_ip}/32"]
  target_tags   = ["ti-cassandra-peer"]

  allow {
    protocol = "tcp"
    ports    = ["9042"]
  }
}

output "peer_private_ips" {
  value = { for name, node in google_compute_address.peer : name => node.address }
}
