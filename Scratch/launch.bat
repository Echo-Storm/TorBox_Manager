@echo off
title TorBox Manager EchoStorm Edition
cd /d "%~dp0"

:: Create venv and install dependencies on first run only
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.10+ is installed and in PATH.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo.
)

:: Launch the app (pythonw suppresses the console window once confirmed working)
venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    echo Check TorBox_Manager_Log.txt in this folder for details.
    pause
)
