@echo off
chcp 65001 >nul
title Trafic PC
call "%~dp0_mediu.bat" || (pause & exit /b 1)
start "" "%PY:python.exe=pythonw.exe%" "%~dp0gui.py" %*
