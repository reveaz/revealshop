@echo off
title RevealLorder Bot
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found in "venv" folder.
    pause
    exit /b 1
)

echo Starting RevealLorder Bot...
call venv\Scripts\activate.bat
python main.py

echo.
echo [BOT STOPPED]
pause
