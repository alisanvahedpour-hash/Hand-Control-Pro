@echo off
rem Optional packages: voice commands (Vosk), MQTT, OBS, macro recording/global hotkeys (pynput)
set PY=%USERPROFILE%\venv\Scripts\python.exe
if not exist "%PY%" (
  echo [ERROR] venv python not found: %PY%
  pause
  exit /b 1
)
"%PY%" -m pip install --default-timeout=300 --retries 10 pynput vosk sounddevice paho-mqtt obsws-python
echo.
echo Done. Voice commands also need a Vosk model folder (see the Voice page in the app).
pause
