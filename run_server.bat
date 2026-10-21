@echo off
REM Start the Polaris MCP Server with ngrok and remote host support
echo ========================================================
echo  Starting Polaris MCP Server for ngrok / remote access
echo ========================================================

set MCP_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*,casing-collector-wrench.ngrok-free.dev,casing-collector-wrench.ngrok-free.dev:*,dummy-mcp.01m5erq7wn81nf6mhfpqkjb0ka.apps.springwinter.dev,dummy-mcp.01m5erq7wn81nf6mhfpqkjb0ka.apps.springwinter.dev:*
set HOST=0.0.0.0
set PORT=8000

echo Allowed hosts: %MCP_ALLOWED_HOSTS%
echo Listening on port: %PORT%
echo.

.venv\Scripts\python.exe server.py
