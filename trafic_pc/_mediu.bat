@echo off
rem Mediul Python al programului (folderul env, creat la prima pornire, ~600 MB).
set "AICI=%~dp0"
set "PY=%AICI%env\python.exe"
set "PATH=%AICI%env;%AICI%env\Library\bin;%AICI%env\Scripts;%PATH%"
set "PYTHONIOENCODING=utf-8"
if exist "%PY%" exit /b 0

echo.
echo  Prima pornire: se instaleaza programele necesare (o singura data, 5-10 minute, cu internet).
echo.
set "MM=%AICI%unelte\micromamba.exe"
if not exist "%MM%" (
  mkdir "%AICI%unelte" 2>nul
  curl.exe -fL --retry 3 -o "%AICI%unelte\mm.tar.bz2" "https://conda.anaconda.org/conda-forge/win-64/micromamba-2.0.5-0.tar.bz2"
  if exist "%AICI%unelte\mm.tar.bz2" tar -xjf "%AICI%unelte\mm.tar.bz2" -C "%AICI%unelte" Library/bin/micromamba.exe
  if exist "%AICI%unelte\Library\bin\micromamba.exe" move /y "%AICI%unelte\Library\bin\micromamba.exe" "%MM%" >nul
  if not exist "%MM%" curl.exe -fL --retry 3 -o "%MM%" "https://github.com/mamba-org/micromamba-releases/releases/download/2.0.5-0/micromamba-win-64"
  if not exist "%MM%" (echo  Nu s-a putut descarca micromamba. Verifica internetul. & exit /b 1)
)
set "MAMBA_ROOT_PREFIX=%AICI%unelte\mamba"
"%MM%" create -y -p "%AICI%env" -c conda-forge python=3.11 opencv numpy openpyxl tk
if not exist "%PY%" (echo  Instalarea Python a esuat. & exit /b 1)
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install onnxruntime
rmdir /s /q "%AICI%unelte\mamba\pkgs" 2>nul
echo  Instalare gata.
exit /b 0
