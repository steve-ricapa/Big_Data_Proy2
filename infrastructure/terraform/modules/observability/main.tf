variable "project_id" { type = string }
variable "prefix" { type = string }
variable "notification_channels" { type = list(string) }
variable "notification_email" {
  type    = string
  default = null
}
resource "google_monitoring_notification_channel" "operator" {
  count        = var.notification_email == null ? 0 : 1
  project      = var.project_id
  display_name = "${var.prefix}: operator"
  type         = "email"
  labels       = { email_address = var.notification_email }
}
locals {
  channels = concat(var.notification_channels, google_monitoring_notification_channel.operator[*].name)
}
resource "google_monitoring_alert_policy" "cpu" {
  project               = var.project_id
  display_name          = "${var.prefix}: CPU VM > 90%"
  combiner              = "OR"
  notification_channels = local.channels
  conditions {
    display_name = "CPU sostenida 10 minutos"
    condition_threshold {
      filter          = "resource.type = \"gce_instance\" AND metric.type = \"compute.googleapis.com/instance/cpu/utilization\" AND metric.label.instance_name = \"${var.prefix}-data\""
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.9
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
}
# Logging nativo de Cloud Run y logs de plataforma de GCE. Sin agente instalado.
resource "google_logging_metric" "errors" {
  project = var.project_id
  name    = "${var.prefix}-run-errors"
  filter  = "resource.type=gce_instance AND logName=\"projects/${var.project_id}/logs/${var.prefix}-health\" AND severity>=ERROR"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}
resource "google_monitoring_alert_policy" "health" {
  for_each = {
    memory_used_percent  = 90
    disk_used_percent    = 80
    unhealthy_containers = 0
    nvd_sync_age_hours   = 30
  }
  project               = var.project_id
  display_name          = "${var.prefix}: ${each.key}"
  combiner              = "OR"
  notification_channels = local.channels
  conditions {
    display_name = "${each.key} above ${each.value}"
    condition_threshold {
      filter          = "resource.type=\"gce_instance\" AND metric.type=\"custom.googleapis.com/threat_intelligence/${each.key}\""
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = each.value
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
}
