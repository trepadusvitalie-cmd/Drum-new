@echo off
chcp 65001 >nul
title Drum RM - marcarea copacilor
call "%~dp0_mediu.bat" || (pause & exit /b 1)
"%PY%" -c "import PIL" 2>nul || "%PY%" -m pip install pillow
"%PY%" "%~dp0antrenare\marcare.py"
