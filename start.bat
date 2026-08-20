@echo off
title EduGenAI Launcher
echo ==========================================
echo   EduGenAI - AI Education Video Platform
echo ==========================================
echo.

echo [1/2] Starting FastAPI Backend on port 8000...
start "EduGenAI Backend" cmd /k "cd /d ""%~dp0backend"" && py -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/2] Waiting 8 seconds for backend to load...
timeout /t 8 /nobreak > nul

echo [3/2] Starting Flutter Web App in Chrome...
start "EduGenAI Flutter" cmd /k "cd /d ""%~dp0flutter_app"" && flutter run -d chrome"

echo.
echo ==========================================
echo   Both services are starting!
echo   Backend:  http://localhost:8000
echo   Frontend: Opens in Chrome automatically
echo ==========================================
pause
