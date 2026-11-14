$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe scripts/prepare_local.py
if ($LASTEXITCODE -ne 0) { throw "Local secret preparation failed" }
& .\.venv\Scripts\python.exe scripts/prepare_airflow3.py
if ($LASTEXITCODE -ne 0) { throw "Airflow secret preparation failed" }
$compose = @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.airflow3.yml", "-f", "docker-compose.secure.yml")
& docker @compose build airflow3-init
if ($LASTEXITCODE -ne 0) { throw "Airflow 3 build failed" }
& docker @compose up -d --wait airflow3-postgres --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw "Airflow 3 metadata startup failed" }
& docker @compose run --rm --no-deps airflow3-init
if ($LASTEXITCODE -ne 0) { throw "Airflow 3 schema initialization failed" }
& docker @compose up -d --wait airflow3-api airflow3-scheduler airflow3-dag-processor --wait-timeout 240
if ($LASTEXITCODE -ne 0) { throw "Airflow 3 startup failed" }
Write-Host "Airflow 3: http://127.0.0.1:18081 | admin; private password in secrets/airflow-admin-password"
Write-Host "DAG initially paused. Run only one ETL at a time. Metadata 2.11 is preserved."
