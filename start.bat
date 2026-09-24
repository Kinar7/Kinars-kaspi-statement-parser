@echo off
cd /d %~dp0

echo Installing dependencies (skipped if already installed)...
python -m pip install -r requirements.txt --quiet

echo.
python main.py %1
