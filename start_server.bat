@echo off
cd /d "%~dp0"
set PYTHONPATH=.
backend\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8001 --host 0.0.0.0
