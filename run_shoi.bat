@echo off
title Shoi (সই) - Health Assistant
echo ========================================================
echo        Shoi (সই) - Voice Health Assistant
echo ========================================================
echo.
echo Starting Shoi server on http://localhost:8000 ...
echo Press Ctrl+C to stop the server anytime.
echo.

.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
pause
