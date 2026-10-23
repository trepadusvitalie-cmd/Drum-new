@echo off
rem Construieste Fibra_Visio.exe (un singur fisier, fara internet la rulare).
rem Ai nevoie de Python 3.10+ de pe python.org (bifeaza "Add python.exe to PATH" la instalare).
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller sv-ttk tkinterdnd2 pywin32
python -m PyInstaller --noconfirm --onefile --windowed --name Fibra_Visio --add-data "sablon;sablon" --collect-all sv_ttk --collect-all tkinterdnd2 --hidden-import win32com.client --hidden-import pythoncom --hidden-import win32print --hidden-import win32ui --hidden-import win32gui --hidden-import win32con gui.py
echo.
echo Gata: dist\Fibra_Visio.exe
pause
