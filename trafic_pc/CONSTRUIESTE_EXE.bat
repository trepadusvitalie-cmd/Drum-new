@echo off
chcp 65001 >nul
title Trafic PC - construirea Trafic_PC.exe
rem Se ruleaza o singura data, pe un calculator unde ai voie sa descarci programe (acasa).
rem Rezultatul: dist\Trafic_PC_portabil.zip si dist\Trafic_PC_autonom.exe
set "AICI=%~dp0"
call "%AICI%_mediu.bat" || (pause & exit /b 1)
rem onnxruntime-directml: modelul ruleaza pe placa video (orice placa cu DirectX 12), altfel pe procesor
"%PY%" -m pip uninstall -y onnxruntime >nul 2>&1
"%PY%" -m pip install pyinstaller onnxruntime-directml
"%PY%" -m PyInstaller --noconfirm --clean --windowed --name Trafic_PC ^
  --distpath "%AICI%dist" --workpath "%AICI%build" --specpath "%AICI%build" ^
  --add-data "%AICI%model;model" ^
  --collect-binaries onnxruntime ^
  --hidden-import detector --hidden-import motor --hidden-import stil --hidden-import openpyxl ^
  --exclude-module torch --exclude-module ultralytics --exclude-module torchvision --exclude-module matplotlib ^
  --paths "%AICI%." "%AICI%gui.py"
if not exist "%AICI%dist\Trafic_PC\Trafic_PC.exe" (echo  Construirea a esuat. & pause & exit /b 1)
if exist "%AICI%dist\Trafic_PC_portabil.zip" del /f /q "%AICI%dist\Trafic_PC_portabil.zip"
pushd "%AICI%dist"
tar -a -c -f Trafic_PC_portabil.zip Trafic_PC
popd
dir /s /b "%AICI%dist\Trafic_PC\_internal\cv2*.pyd" >nul 2>&1 || echo  ATENTIE: lipseste OpenCV (cv2*.pyd) din _internal!
echo.
echo  Construiesc si varianta intr-un singur fisier: dist\Trafic_PC_autonom.exe ...
"%PY%" -m PyInstaller --noconfirm --onefile --windowed --name Trafic_PC_autonom ^
  --distpath "%AICI%dist" --workpath "%AICI%build1" --specpath "%AICI%build1" ^
  --add-data "%AICI%model;model" ^
  --collect-binaries onnxruntime ^
  --hidden-import detector --hidden-import motor --hidden-import stil --hidden-import openpyxl ^
  --exclude-module torch --exclude-module ultralytics --exclude-module torchvision --exclude-module matplotlib ^
  --paths "%AICI%." "%AICI%gui.py"
if exist "%AICI%dist\Trafic_PC_autonom.exe" (echo  Gata: dist\Trafic_PC_autonom.exe) else (echo  Varianta autonoma a esuat - foloseste arhiva portabila.)
echo.
echo  Gata: dist\Trafic_PC_portabil.zip - dezarhivezi si pornesti Trafic_PC.exe
pause
