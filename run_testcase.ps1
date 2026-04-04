Write-Host "Iniciando Test Case Generator..."

Set-Location "E:\Portfolio\bot_test_case"

# Verifica si ya está corriendo run.py
$running = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*run.py*"
}

if ($running) {
    Write-Host "La app ya está corriendo"
    Start-Process "http://127.0.0.1:8000"
} else {
    Write-Host "Iniciando app..."

    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& 'E:\Portfolio\bot_test_case\venv\Scripts\python.exe' run.py"
}