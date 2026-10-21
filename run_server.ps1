# Start Polaris MCP Server with ngrok and SpringWinter host permissions
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Starting Polaris MCP Server for ngrok / SpringWinter" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$env:MCP_ALLOWED_HOSTS = "localhost:*,127.0.0.1:*,[::1]:*,casing-collector-wrench.ngrok-free.dev,casing-collector-wrench.ngrok-free.dev:*,dummy-mcp.01m5erq7wn81nf6mhfpqkjb0ka.apps.springwinter.dev,dummy-mcp.01m5erq7wn81nf6mhfpqkjb0ka.apps.springwinter.dev:*"
$env:HOST = "0.0.0.0"
$env:PORT = "8000"

Write-Host "Allowed hosts: $env:MCP_ALLOWED_HOSTS" -ForegroundColor Green
Write-Host "Server listening on port 8000..." -ForegroundColor Green
Write-Host ""

& .venv\Scripts\python.exe server.py
