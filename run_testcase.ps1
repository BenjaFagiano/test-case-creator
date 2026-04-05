Write-Host "Iniciando Test Case Generator..."

$projectPath = "E:\Portfolio\bot_test_case"
$pythonPath = "$projectPath\venv\Scripts\python.exe"

Set-Location $projectPath

# 🔥 Detectar puerto 8000 correctamente en PowerShell
$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

if ($portInUse) {
    Write-Host "La app ya está corriendo"
    Start-Process "http://127.0.0.1:8000"
} else {
    Write-Host "Iniciando app..."

    Start-Process $pythonPath -ArgumentList "run.py"
}