variable "project_id" { type = string }
variable "region" { type = string }
variable "name" { type = string }
variable "identity" { type = string }
variable "network" { type = string }
variable "subnet" { type = string }
variable "secret_ids" { type = map(string) }
variable "protect" { type = bool }
variable "config" {
  type = object({
    image          = string
    port           = number
    invokers       = set(string)
    env            = map(string)
    secret_env     = map(string)
    secret_version = string
  })
}
resource "google_secret_manager_secret_iam_member" "access" {
  for_each  = toset(values(var.config.secret_env))
  project   = var.project_id
  secret_id = var.secret_ids[each.value]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.identity}"
}
resource "google_cloud_run_v2_service" "main" {
  name                = var.name
  location            = var.region
  deletion_protection = var.protect
  # Endpoint HTTPS externo pero IAM obligatorio; necesario para clientes remotos.
  ingress = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = var.identity
    timeout                          = "300s"
    max_instance_request_concurrency = 10
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = var.network
        subnetwork = var.subnet
        tags       = [replace(var.name, "/-(api|mcp|dashboard)$/", "-web")]
      }
    }
    containers {
      image = var.config.image
      ports { container_port = var.config.port }
      resources {
        limits            = { cpu = "1", memory = "512Mi" }
        cpu_idle          = true
        startup_cpu_boost = false
      }
      dynamic "env" {
        for_each = var.config.env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = var.config.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = var.secret_ids[env.value]
              version = var.config.secret_version
            }
          }
        }
      }
      startup_probe {
        tcp_socket { port = var.config.port }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 10
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.access]
}
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = var.config.invokers
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = each.value
}
output "url" { value = google_cloud_run_v2_service.main.uri }
