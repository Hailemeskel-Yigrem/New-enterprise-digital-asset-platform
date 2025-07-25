# VaultForge local development bootstrap (PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "Poetry not found. Install from https://python-poetry.org/"
}

poetry install --no-interaction
docker compose up -d postgres redis rabbitmq

Write-Host "Waiting for postgres..."
do {
    Start-Sleep -Seconds 1
    docker compose exec -T postgres pg_isready -U vaultforge 2>$null | Out-Null
} while ($LASTEXITCODE -ne 0)

poetry run alembic upgrade head
Write-Host "VaultForge dev bootstrap complete. Run: poetry run vaultforge"
