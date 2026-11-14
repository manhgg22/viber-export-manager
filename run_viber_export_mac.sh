#!/bin/bash
# ============================================================
#  run_viber_export_mac.sh  -  Xuat Viber Desktop tren macOS (cho KHACH)
#  CHUA TEST tren Mac that - phai chay tren may Mac co Viber da dang nhap.
#
#  Chuan bi 1 lan:
#    1) Cai Xcode Command Line Tools:   xcode-select --install
#    2) Tai engine Mac:
#         git clone https://github.com/Anastasia-D-Kravchenko/viber-export-macos.git
#    3) Dat file nay + viber_locate.py + viber_process.py cung thu muc cha
#       voi thu muc viber-export-macos/
# ============================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$HERE/viber-export-macos"
OUT="$HERE/export_mac"
mkdir -p "$OUT"

echo "[1/3] Preflight (do vi tri viber.db)..."
python3 "$HERE/viber_locate.py" || true   # chi de bao cao, khong chan

echo
echo "[2/3] Export tu Viber (engine lldb). Nen THOAT Viber truoc khi chay."
chmod +x "$ENGINE/viber-export-macos.sh"
# -o: thu muc ra ; -y: bo qua hoi xac nhan
"$ENGINE/viber-export-macos.sh" -o "$OUT" -y

CSV="$OUT/viber_export.csv"
if [ ! -f "$CSV" ]; then
  echo "[X] Khong thay $CSV - engine co the da doi ten file ra. Kiem tra trong $OUT"
  ls -la "$OUT"
  exit 1
fi

echo
echo "[3/3] Xu ly cho C-level..."
python3 "$HERE/viber_process.py" "$CSV" --out "$OUT/processed"

echo
echo "XONG. Ket qua o: $OUT/processed"
echo "  - overview.md         (tom tat cho C-level)"
echo "  - groups_summary.csv  (moi group 1 dong)"
echo "  - messages_all.csv    (toan bo tin, de dua cho Grok)"
