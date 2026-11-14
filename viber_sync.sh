#!/usr/bin/env bash
# ============================================================
#  viber_sync.sh - 1 lenh: export -> doc DB -> bao cao  (LINUX)
#  Tuong duong viber_sync.bat cua Windows, dung CHUNG engine Frida
#  (Viber for Linux la ung dung Qt giong ban Windows).
#  Dieu kien: Viber Desktop dang chay + da dang nhap.
#
#  LUU Y: duong Frida tren Linux la THU NGHIEM - chua test tren
#  may Linux that. Neu bao "symbol not found", xem muc Linux trong README.
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY="${PYTHON:-python3}"
ENGINE_DB="vendor/ViberPC-Export/export/viber_export.db"

echo "[0/3] Preflight (do vi tri viber.db)..."
"$PY" viber_locate.py || true

echo "[1/3] Export tu Viber (Frida)..."
"$PY" vendor/ViberPC-Export/viber.py export --no-log --timeout 90 || true
if [ ! -f "$ENGINE_DB" ]; then
  echo "[X] Chua co file export ($ENGINE_DB). Viber co dang chay khong?"
  echo "    Neu thay 'symbol not found' o tren: Qt cua Viber Linux chua ho tro - xem README muc Linux."
  exit 1
fi

echo "[2/3] Doc DB -> CSV..."
"$PY" viber_db_to_csv.py "$ENGINE_DB" -o live_from_db.csv

echo "[3/3] Ra bao cao C-level..."
"$PY" viber_process.py live_from_db.csv --out processed_real

echo
echo "XONG. Ket qua:"
echo "  - live_from_db.csv                 (toan bo tin, dinh dang bang)"
echo "  - processed_real/overview.md       (tom tat cho C-level)"
echo "  - processed_real/messages_all.csv  (dua cho Grok phan tich)"
