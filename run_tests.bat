@echo off
cd /d "%~dp0"
set PY=%USERPROFILE%\venv\Scripts\python.exe
if not exist "%PY%" set PY=python
"%PY%" -m unittest discover -s tests -t . -v
pause
