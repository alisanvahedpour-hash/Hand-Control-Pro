@echo off
rem Code signing template. Needs a code-signing certificate (.pfx) and signtool (Windows SDK).
rem Usage:  sign_windows.bat  path\to\certificate.pfx  password
if "%~2"=="" (
  echo Usage: sign_windows.bat certificate.pfx password
  exit /b 1
)
signtool sign /f "%~1" /p "%~2" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 dist\HandControlPro.exe
if exist Output\HandControlPro_Setup.exe signtool sign /f "%~1" /p "%~2" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 Output\HandControlPro_Setup.exe
pause
