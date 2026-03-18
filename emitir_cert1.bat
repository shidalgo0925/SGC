@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" script\generar.py --cert1 %*
) else (
  python script\generar.py --cert1 %*
)
echo.
pause
