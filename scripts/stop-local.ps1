$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
# Stops only this Compose project. Does not delete persistent volumes or datasets.
docker compose -f docker-compose.yml -f docker-compose.airflow3.yml -f docker-compose.secure.yml --profile web --profile orchestration --profile migration stop
if ($LASTEXITCODE -ne 0) { throw "Stop failed" }
