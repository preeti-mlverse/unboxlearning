@echo off
rem Starts the UnboxEd engine (API on :8030) and web app (:5190), then opens the browser.
cd /d %~dp0
start "UnboxEd API" cmd /k python -m uvicorn engine.api:app --port 8030
start "UnboxEd Web" cmd /k npm --prefix web run dev
timeout /t 6 >nul
start http://localhost:5190
