Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "       Shoi (সই) - Bangla AI Voice Health Assistant     " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Starting Shoi backend and PWA on http://localhost:8000" -ForegroundColor Green
Write-Host "Open your browser at: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Interactive API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to terminate." -ForegroundColor Gray
Write-Host ""

& ".\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
