#!/usr/bin/env python3
"""
viber_locate.py - Tu do vi tri Viber Desktop DB + kiem tra dieu kien truoc khi export.
Chay duoc tren Windows va macOS. Khong sua gi, chi doc va bao cao (JSON).

Dung lam buoc "preflight" cho tool export mot-chao danh cho nguoi dung cuoi.
"""
import os
import sys
import json
import glob
import platform
import shutil
import subprocess

SQLITE_MAGIC = b"SQLite format 3\x00"


def candidate_roots():
    """Cac thu muc goc co the chua ViberPC theo tung he dieu hanh."""
    sysname = platform.system()
    roots = []
    if sysname == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots.append(os.path.join(appdata, "ViberPC"))
    elif sysname == "Darwin":  # macOS
        home = os.path.expanduser("~")
        roots.append(os.path.join(home, "Library", "Application Support", "ViberPC"))
    else:  # Linux
        home = os.path.expanduser("~")
        roots.append(os.path.join(home, ".ViberPC"))
    return [r for r in roots if r]


def find_databases():
    """Tim tat ca viber.db (moi so dien thoai la 1 tai khoan)."""
    found = []
    for root in candidate_roots():
        if not os.path.isdir(root):
            continue
        # moi tai khoan = 1 thu muc con ten theo so dien thoai
        for path in glob.glob(os.path.join(root, "*", "viber.db")):
            try:
                st = os.stat(path)
                account = os.path.basename(os.path.dirname(path))
                found.append({
                    "account": account,
                    "path": path,
                    "size_bytes": st.st_size,
                    "modified": _fmt_time(st.st_mtime),
                    "encrypted": _is_encrypted(path),
                    "has_wal": os.path.exists(path + "-wal"),
                })
            except OSError as e:
                found.append({"path": path, "error": str(e)})
    return found


def _is_encrypted(path):
    """DB chua ma hoa bat dau bang 'SQLite format 3'. Khac di = da ma hoa."""
    try:
        with open(path, "rb") as f:
            return f.read(16) != SQLITE_MAGIC
    except OSError:
        return None


def _fmt_time(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def viber_running():
    """Viber dang chay khong? (can dang chay cho phuong phap live-attach)."""
    sysname = platform.system()
    try:
        if sysname == "Windows":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Viber.exe", "/NH"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            return "Viber.exe" in out
        else:
            out = subprocess.run(["pgrep", "-i", "viber"],
                                 capture_output=True, text=True, timeout=10).stdout
            return bool(out.strip())
    except Exception:
        return None


def report():
    dbs = find_databases()
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 10),
        "viber_running": viber_running(),
        "databases_found": len(dbs),
        "databases": dbs,
    }
    # ket luan de nguoi dung hieu
    notes = []
    if not dbs:
        notes.append("KHONG tim thay viber.db. Viber Desktop da cai va dang nhap chua?")
    for db in dbs:
        if db.get("encrypted"):
            notes.append(f"[{db.get('account')}] DB da MA HOA -> can phuong phap live-attach (Viber phai dang chay).")
        elif db.get("encrypted") is False:
            notes.append(f"[{db.get('account')}] DB chua ma hoa -> doc truc tiep bang SQLite duoc.")
    if not info["python_ok"]:
        notes.append("Python < 3.10, nen nang cap.")
    info["notes"] = notes
    return info


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, ensure_ascii=False))
