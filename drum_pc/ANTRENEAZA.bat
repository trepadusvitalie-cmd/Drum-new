@echo off
chcp 65001 >nul
title Drum RM - antrenarea modelului
call "%~dp0_mediu.bat" || (pause & exit /b 1)
"%PY%" -c "import ultralytics, psutil" 2>nul || "%PY%" -m pip install ultralytics psutil
rem prioritate scazuta: calculatorul ramane utilizabil in timpul antrenarii
start "" /b /belownormal /wait "%PY%" "%~dp0antrenare\antreneaza.py" %*
pause
