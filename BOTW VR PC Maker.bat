@echo off
rem Builds a transfer-ready BOTW VR package from a GitHub ref and your own local game files.
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required. Run tools\setup_windows.ps1 first.
    pause
    exit /b 1
)
py -3 tools\vr\maker.py
if errorlevel 1 pause
