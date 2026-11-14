@echo off
REM Cai dat 1 lan cac thu vien can thiet (Frida).
echo === Kiem tra Python ===
python --version
if errorlevel 1 (
  echo [X] Chua co Python. Tai tai: https://www.python.org/downloads/  (nho tick "Add to PATH")
  pause & exit /b 1
)
echo.
echo === Cai Frida ===
python -m pip install --upgrade pip
python -m pip install frida frida-tools
echo.
echo === Xong. Bay gio mo Viber Desktop, dang nhap, roi chay viber_sync.bat ===
pause
