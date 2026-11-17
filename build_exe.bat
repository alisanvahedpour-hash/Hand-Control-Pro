@echo off
setlocal
cd /d "%~dp0"

set PY=%USERPROFILE%\venv\Scripts\python.exe
if not exist "%PY%" (
  echo [ERROR] venv python not found: %PY%
  echo Edit the PY line in this file to point to your venv python.exe
  pause
  exit /b 1
)

if not exist "hand_control_pro.py" (
  echo [ERROR] hand_control_pro.py must be in the same folder as this file.
  pause
  exit /b 1
)

set MODE=--windowed
if /i "%1"=="debug" set MODE=--console

echo.
echo === Creating icon ===
if exist "make_icon.py" "%PY%" make_icon.py
set ICON=
if exist "app_icon.ico" set ICON=--icon app_icon.ico

echo.
echo === Installing PyInstaller ===
"%PY%" -m pip install --default-timeout=300 --retries 10 pyinstaller
if errorlevel 1 (
  echo [ERROR] pip install failed. Run this file again.
  pause
  exit /b 1
)

echo.
echo === Building single-file exe (this takes a few minutes) ===
"%PY%" -m PyInstaller --noconfirm --clean --onefile %MODE% %ICON% --name HandControlPro --collect-all mediapipe --hidden-import pyperclip hand_control_pro.py
if errorlevel 1 (
  echo [ERROR] Build failed. Copy the error text and send it.
  pause
  exit /b 1
)

echo.
echo === DONE ===
echo Run: %~dp0dist\HandControlPro.exe
echo Optional installer: install Inno Setup, then open installer.iss and press Compile.
pause
