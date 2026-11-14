#!/usr/bin/env bash
# Cai dat 1 lan cac thu vien can thiet (Frida) - cho LINUX / macOS.
set -e
PY="${PYTHON:-python3}"

echo "=== Kiem tra Python ==="
"$PY" --version || { echo "[X] Chua co python3. Cai python3 >= 3.10 roi chay lai."; exit 1; }

echo
echo "=== Cai Frida ==="
"$PY" -m pip install --upgrade pip
"$PY" -m pip install frida frida-tools

echo
echo "=== Xong ==="
echo "Linux: mo Viber Desktop, dang nhap, roi chay:  ./viber_sync.sh"
echo "macOS: dung engine rieng, chay:                ./run_viber_export_mac.sh"
