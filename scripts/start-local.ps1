param([switch]$WithAirflow)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe scripts/prepare_local.py
if ($LASTEXITCODE -ne 0) { throw "Secret preparation failed" }
& .\.venv\Scripts\python.exe scripts/prepare_security.py
if ($LASTEXITCODE -ne 0) { throw "Security secret preparation failed" }
$compose = @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.airflow3.yml", "-f", "docker-compose.secure.yml")
& docker @compose build runner
if ($LASTEXITCODE -ne 0) { throw "Build failed" }
& docker @compose up -d --wait mongodb cassandra neo4j --wait-timeout 360
if ($LASTEXITCODE -ne 0) { throw "Database startup failed" }
& docker @compose run --rm --no-deps mongo-init
if ($LASTEXITCODE -ne 0) { throw "Mongo application user initialization failed" }
& docker @compose run --rm --no-deps cassandra-init
if ($LASTEXITCODE -ne 0) { throw "Cassandra application user initialization failed" }
& docker @compose --profile web up -d --wait api dashboard --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw "Web startup failed" }
if ($WithAirflow) {
    & "$PSScriptRoot/start-airflow3.ps1"
    if ($LASTEXITCODE -ne 0) { throw "Airflow 3 startup failed" }
}
Write-Host "Dashboard http://127.0.0.1:18501 | API http://127.0.0.1:18000/docs | Airflow 3 http://127.0.0.1:18081 with -WithAirflow"
