#!/usr/bin/env python3
"""
viber_ingest_server.py - Chỗ NHẬN tin Viber liên tục (phần "quản lý" chạy 24/7).

App Android "notification forwarder" bắn moi tin Viber moi (dang webhook POST JSON)
vao day. Server ghi lai thanh live_messages.csv - CHINH LA dinh dang CSV ma
viber_process.py doc duoc (DateTime, ChatID, Contact, Direction, MsgType, Message).

Chi dung thu vien co san cua Python (http.server) - KHONG can pip install.
Chi chay cuc bo, khong goi mang ra ngoai.

Chay:
  python viber_ingest_server.py            # lang nghe 0.0.0.0:8787
  python viber_ingest_server.py --port 9000 --out mydata.csv

App Android tro webhook toi:  http://<IP-may-nay>:8787/hook
Payload linh hoat - chap nhan cac ten truong hay gap:
  title / appTitle / group   -> ten group (ChatID)
  text  / message / content  -> noi dung (co the dang "Nguoi gui: loi nhan")
  time  / timestamp          -> thoi gian (tuy chon; thieu thi lay gio server)
"""
import argparse
import csv
import json
import os
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FIELDS = ["DateTime", "ChatID", "Contact", "Direction", "MsgType", "Message"]
_lock = threading.Lock()
OUT = "live_messages.csv"


def _pick(d, *names):
    for n in names:
        if isinstance(d, dict) and d.get(n):
            return str(d[n])
    return ""


def parse_notification(d):
    """Bien 1 thong bao Viber thanh 1 dong CSV.
    Viber group: title = ten group, text = 'Nguoi gui: noi dung'.
    Viber 1-1 : title = ten nguoi, text = noi dung.
    """
    title = _pick(d, "title", "appTitle", "group", "conversation")
    text = _pick(d, "text", "message", "content", "body")
    when = _pick(d, "time", "timestamp", "postTime")
    try:
        dt = datetime.fromtimestamp(int(when) / 1000).strftime("%Y-%m-%d %H:%M:%S") if when.isdigit() \
            else (when or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except (ValueError, OSError):
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sender, body = "", text
    m = re.match(r"^\s*([^:]{1,40}):\s*(.*)$", text, re.S)  # tach 'Nguoi gui: loi' neu co
    if m:
        sender, body = m.group(1).strip(), m.group(2).strip()
    if not sender:
        sender = title  # 1-1: nguoi gui = ten chat

    return {
        "DateTime": dt,
        "ChatID": title or "(unknown)",
        "Contact": sender or "(unknown)",
        "Direction": "IN",
        "MsgType": "text",
        "Message": body,
    }


def append_row(row):
    with _lock:
        new = not os.path.exists(OUT)
        with open(OUT, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/health"):
            n = 0
            if os.path.exists(OUT):
                with open(OUT, encoding="utf-8-sig") as f:
                    n = max(0, sum(1 for _ in f) - 1)
            self._send(200, {"status": "ok", "stored_messages": n, "file": os.path.abspath(OUT)})
        else:
            self._send(200, {"status": "ok", "hint": "POST JSON to /hook"})

    def do_POST(self):
        if not self.path.startswith("/hook"):
            return self._send(404, {"error": "use /hook"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            d = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as e:
            return self._send(400, {"error": f"bad json: {e}"})
        row = parse_notification(d)
        if not row["Message"] and row["ChatID"] == "(unknown)":
            return self._send(400, {"error": "empty notification"})
        append_row(row)
        self._send(200, {"status": "stored", "chat": row["ChatID"]})
        try:  # log gon; khong duoc de loi encoding console lam hong phan hoi
            line = f"[+] {row['DateTime']} | {row['ChatID']} | {row['Contact']}: {row['Message'][:50]}"
            print(line.encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass

    def log_message(self, *a):
        pass  # tat log mac dinh, tu in dong gon o tren


def main():
    global OUT
    ap = argparse.ArgumentParser(description="Server nhan tin Viber tu Android forwarder")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--out", default="live_messages.csv")
    a = ap.parse_args()
    OUT = a.out
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"[i] Dang nghe http://{a.host}:{a.port}/hook  ->  ghi vao {os.path.abspath(OUT)}")
    print("[i] App Android tro webhook toi dia chi tren. Ctrl+C de dung.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[i] Dung server.")


if __name__ == "__main__":
    main()
