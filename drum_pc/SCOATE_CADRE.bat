@echo off
chcp 65001 >nul
title Drum RM - cadre pentru antrenare
call "%~dp0_mediu.bat" || (pause & exit /b 1)
set "SRC=%~1"
if "%SRC%"=="" set "SRC=%~dp0filmari"
"%PY%" "%~dp0antrenare\scoate_cadre.py" "%SRC%"
pause
