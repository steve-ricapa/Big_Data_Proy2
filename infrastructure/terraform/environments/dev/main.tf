# No google_project_service: habilitación de APIs manual y aprobada.
module "network" {
  source       = "../../modules/networking"
  prefix       = var.prefix
  region       = var.region
  cidr         = var.subnet_cidr
  public_https = var.public_https
}
module "iam" {
  source     = "../../modules/iam"
  project_id = var.project_id
  prefix     = var.prefix
}
module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  prefix      = var.prefix
  region      = var.region
  vm_identity = module.iam.vm_email
}
module "secrets" {
  source      = "../../modules/secrets"
  project_id  = var.project_id
  prefix      = var.prefix
  vm_identity = module.iam.vm_email
}
module "registry" {
  source     = "../../modules/registry"
  project_id = var.project_id
  prefix     = var.prefix
  region     = var.region
  reader     = module.iam.vm_email
  writer     = module.iam.vm_email
}
module "compute" {
  source                    = "../../modules/compute"
  prefix                    = var.prefix
  zone                      = var.zone
  machine_type              = var.machine_type
  boot_image                = var.boot_image
  boot_disk_gb              = var.boot_disk_gb
  data_disk_gb              = var.data_disk_gb
  disk_type                 = var.disk_type
  subnet                    = module.network.subnet_id
  service_account           = module.iam.vm_email
  external_ip               = var.allow_external_egress_ip
  reserved_external_address = var.reserved_external_address
  protect                   = var.deletion_protection
  startup_script            = file("${path.module}/../../../scripts/vm-bootstrap.sh")
}
module "cloud_run" {
  for_each   = var.web_services
  source     = "../../modules/cloud_run"
  project_id = var.project_id
  region     = var.region
  name       = "${var.prefix}-${each.key}"
  config     = each.value
  identity   = module.iam.web_emails[each.key]
  network    = module.network.network_id
  subnet     = module.network.subnet_id
  secret_ids = module.secrets.ids
  protect    = var.deletion_protection
}
module "observability" {
  source                = "../../modules/observability"
  project_id            = var.project_id
  prefix                = var.prefix
  notification_channels = var.notification_channels
  notification_email    = var.notification_email
}
