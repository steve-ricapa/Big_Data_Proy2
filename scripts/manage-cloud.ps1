param([ValidateSet("status", "start", "stop")][string]$Action = "status")
$ErrorActionPreference = "Stop"
$project = "proyectobigdata2-514216"
$zone = "us-central1-a"
$vm = "ti-dev-data"
if ($Action -eq "status") {
    gcloud compute instances describe $vm --project=$project --zone=$zone --format="table(name,status,networkInterfaces[0].networkIP)"
} elseif ($Action -eq "stop") {
    Write-Warning "Stop pauses availability. Ensure DAG/CLI are idle first. Data disks and reserved IP remain billable. No resources are deleted."
    gcloud compute instances stop $vm --project=$project --zone=$zone --quiet
} else {
    gcloud compute instances start $vm --project=$project --zone=$zone --quiet
}
if ($LASTEXITCODE -ne 0) { throw "GCP VM operation failed" }
