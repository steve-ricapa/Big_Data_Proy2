output "vm_name" { value = module.compute.name }
output "vm_private_ip" { value = module.compute.private_ip }
output "data_disk" { value = module.compute.disk_name }
output "buckets" { value = module.storage.names }
output "repository" { value = module.registry.id }
output "secret_ids" { value = module.secrets.ids }
output "vm_service_account" { value = module.iam.vm_email }
output "web_service_accounts" { value = module.iam.web_emails }
output "service_urls" { value = { for k, v in module.cloud_run : k => v.url } }
