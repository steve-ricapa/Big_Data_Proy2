variable "project_id" { type = string }
variable "notification_email" {
  type    = string
  default = null
}
variable "reserved_external_address" {
  description = "Reserve the assigned public HTTPS address for stable OAuth/DNS; no database ports."
  type        = string
  default     = null
}
variable "operator_member" {
  description = "Explicit operator IAM member for IAP/OS Login; no public administration."
  type        = string
  default     = null
}
variable "public_https" {
  description = "Publish only Caddy HTTP redirect/ACME and HTTPS; never DB/SSH."
  type        = bool
  default     = false
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "zone" {
  type    = string
  default = "us-central1-a"
}
variable "prefix" {
  type    = string
  default = "ti-dev"
}
variable "subnet_cidr" {
  type    = string
  default = "10.42.0.0/24"
}
variable "machine_type" {
  type    = string
  default = "e2-standard-4"
}
variable "boot_disk_gb" {
  type    = number
  default = 30
}
variable "data_disk_gb" {
  type    = number
  default = 100
}
variable "disk_type" {
  type    = string
  default = "pd-balanced"
}
variable "boot_image" {
  description = "Nombre exacto de imagen Debian 12 aprobado, no una familia mutable."
  type        = string
}
variable "allow_external_egress_ip" {
  description = "Aprobar IP efímera para apt/Docker Hub; ningún ingreso público permitido."
  type        = bool
  default     = false
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "notification_channels" {
  type    = list(string)
  default = []
}
variable "web_services" {
  description = "Vacío hasta tener aplicaciones reales, imágenes por digest y TLS de bases."
  type = map(object({
    image          = string
    port           = number
    invokers       = set(string)
    env            = map(string)
    secret_env     = map(string)
    secret_version = string
  }))
  default = {}
  validation {
    condition = alltrue([for k, s in var.web_services :
      contains(["api", "mcp", "dashboard"], k) &&
      can(regex("@sha256:[0-9a-f]{64}$", s.image)) &&
      !contains(s.invokers, "allUsers") && !contains(s.invokers, "allAuthenticatedUsers") &&
      alltrue([for secret in values(s.secret_env) : contains(["mongodb-uri", "cassandra-password", "neo4j-password", "mcp-token"], secret)])
    ])
    error_message = "Solo api/mcp/dashboard, imágenes por digest, secretos conocidos e invocadores explícitos; no acceso público."
  }
}
