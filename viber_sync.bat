@echo off
REM ============================================================
REM  viber_sync.bat - 1 lenh: export -> doc DB -> bao cao
REM  Chay ngam duoc (Task Scheduler) - KHONG can ai bam gi.
REM  Dieu kien: Viber Desktop dang chay + da dang nhap.
REM ============================================================
setlocal
cd /d "%~dp0"
set STAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
set STAMP=%STAMP: =0%

echo [1/3] Export tu Viber (Frida)...
python vendor\ViberPC-Export\viber.py export --no-log --timeout 90
if not exist "vendor\ViberPC-Export\export\viber_export.db" (
  echo [X] Chua co file export. Viber co dang chay khong?
  exit /b 1
)

echo [2/3] Doc DB -> CSV...
python viber_db_to_csv.py vendor\ViberPC-Export\export\viber_export.db -o live_from_db.csv
if errorlevel 1 exit /b 1

echo [3/3] Ra bao cao C-level...
python viber_process.py live_from_db.csv --out processed_real
if errorlevel 1 exit /b 1

echo.
echo XONG luc %STAMP%. Ket qua:
echo   - live_from_db.csv        (toan bo tin, dinh dang bang)
echo   - processed_real\overview.md
echo   - processed_real\messages_all.csv  (dua cho Grok)
