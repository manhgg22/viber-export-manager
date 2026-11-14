#!/usr/bin/env python3
"""
viber_web.py - Trang web xem tin nhan Viber TU CAP NHAT (real-time demo).

- Phuc vu 1 trang HTML tu lam moi moi 2s, hien tin moi nhat len dau.
- /data tra JSON doc tu live_from_db.csv.
- Voi --live: chay 1 luong nen cu moi REFRESH giay thi export tu Viber + doc DB
  lai -> live_from_db.csv (de tin moi tu dong hien ra).

Chi chay cuc bo. Khong gui du lieu di dau.

  python viber_web.py                  # chi hien du lieu dang co
  python viber_web.py --live --refresh 15   # tu export moi 15s (can Viber chay)
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "live_from_db.csv")
DB = os.path.join(HERE, "vendor", "ViberPC-Export", "export", "viber_export.db")
_state = {"last_refresh": None, "last_count": 0, "refreshing": False, "error": None}


def read_rows():
    rows = []
    if os.path.exists(CSV):
        try:
            with open(CSV, encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
        except OSError:
            pass
    rows.sort(key=lambda r: r.get("DateTime", ""), reverse=True)  # moi nhat len dau
    return rows


PAGE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Viber Live</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--line:#21262d;--tx:#e6edf3;--mut:#8b949e;--in:#2563eb;--out:#16a34a;--acc:#a855f7}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--tx);font-size:14px}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
h1{font-size:16px;font-weight:700}
.pill{background:#0d1117;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12px;color:var(--mut)}
.pill b{color:var(--tx)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#2ea043;margin-right:6px;animation:p 1.4s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
main{max-width:860px;margin:0 auto;padding:16px}
.msg{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px;animation:f .4s}
.msg.new{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}
@keyframes f{from{opacity:0;transform:translateY(-6px)}to{opacity:1}}
.row1{display:flex;gap:8px;align-items:center;margin-bottom:4px;flex-wrap:wrap}
.chat{font-weight:600}
.badge{font-size:10px;padding:1px 7px;border-radius:999px;font-weight:700}
.badge.IN{background:rgba(37,99,235,.18);color:#6ea8ff}
.badge.OUT{background:rgba(22,163,74,.18);color:#56d364}
.who{color:var(--mut);font-size:12px}
.time{color:var(--mut);font-size:11px;margin-left:auto}
.body{white-space:pre-wrap;word-break:break-word;line-height:1.45}
.kind{font-size:10px;color:var(--acc);text-transform:uppercase}
.empty{text-align:center;color:var(--mut);padding:40px}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:6px 14px;font-weight:700;cursor:pointer;font-size:13px}
button:disabled{opacity:.5;cursor:wait}
</style></head><body>
<header>
  <h1>📩 Viber Live</h1>
  <span class="pill"><span class="dot"></span>Tu cap nhat 2s</span>
  <span class="pill">Tong: <b id="cnt">0</b></span>
  <span class="pill">Cap nhat: <b id="upd">-</b></span>
  <span class="pill" id="st">-</span>
  <button id="btn" onclick="refreshNow()">🔄 Lam moi ngay</button>
</header>
<main><div id="list"><div class="empty">Dang tai...</div></div></main>
<script>
let seen=new Set(), first=true;
function esc(s){return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function tick(){
  try{
    const r=await fetch('/data',{cache:'no-store'}); const d=await r.json();
    document.getElementById('cnt').textContent=d.rows.length;
    document.getElementById('upd').textContent=new Date().toLocaleTimeString();
    const s=document.getElementById('st'), b=document.getElementById('btn');
    s.textContent = d.refreshing? '⏳ dang export (~90s)...' : (d.last_refresh? ('export luc: '+d.last_refresh):'chua export');
    b.disabled = d.refreshing;
    if(d.error) s.textContent='loi: '+String(d.error).slice(0,40);
    const list=document.getElementById('list');
    if(!d.rows.length){list.innerHTML='<div class="empty">Chua co tin. Nhan tin trong Viber...</div>';return;}
    list.innerHTML='';
    for(const m of d.rows){
      const id=m.DateTime+'|'+m.Message;
      const isNew=!first && !seen.has(id);
      seen.add(id);
      const el=document.createElement('div');
      el.className='msg'+(isNew?' new':'');
      el.innerHTML=`<div class="row1">
        <span class="chat">${esc(m.ChatID)}</span>
        <span class="badge ${m.Direction}">${m.Direction}</span>
        <span class="who">${esc(m.Contact)}</span>
        <span class="time">${esc(m.DateTime)} UTC</span></div>
        <div class="body">${esc(m.Message)}</div>
        ${m.MsgType&&m.MsgType!=='text'?'<span class="kind">'+esc(m.MsgType)+'</span>':''}`;
      list.appendChild(el);
    }
    first=false;
  }catch(e){document.getElementById('st').textContent='loi: '+e;}
}
async function refreshNow(){
  document.getElementById('btn').disabled=true;
  document.getElementById('st').textContent='⏳ dang export (~90s)...';
  try{await fetch('/refresh',{cache:'no-store'});}catch(e){}
}
tick(); setInterval(tick,2000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/data"):
            payload = {"rows": read_rows(), "last_refresh": _state["last_refresh"],
                       "refreshing": _state["refreshing"], "error": _state["error"]}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")
        elif self.path.startswith("/refresh"):
            if not _state["refreshing"]:
                threading.Thread(target=do_one_refresh, daemon=True).start()
                self._send(200, json.dumps({"started": True}), "application/json")
            else:
                self._send(200, json.dumps({"started": False, "busy": True}), "application/json")
        else:
            self._send(200, PAGE, "text/html; charset=utf-8")

    def log_message(self, *a):
        pass


def do_one_refresh(export_timeout=45):
    """Chay 1 lan: export tu Viber -> doc DB -> CSV. Tra True neu xong."""
    if _state["refreshing"]:
        return False
    _state["refreshing"] = True
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "vendor", "ViberPC-Export", "viber.py"),
                        "export", "--no-log", "--timeout", str(export_timeout)],
                       cwd=HERE, capture_output=True, timeout=export_timeout + 60)
        if os.path.exists(DB):
            subprocess.run([sys.executable, os.path.join(HERE, "viber_db_to_csv.py"), DB, "-o", CSV],
                           cwd=HERE, capture_output=True, timeout=60)
        _state["last_refresh"] = time.strftime("%H:%M:%S")
        _state["error"] = None
        return True
    except Exception as e:
        _state["error"] = str(e)
        return False
    finally:
        _state["refreshing"] = False


def refresh_loop(refresh_sec, export_timeout):
    while True:
        do_one_refresh(export_timeout)
        time.sleep(refresh_sec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=17653)
    ap.add_argument("--live", action="store_true", help="bat vong lap tu export tu Viber")
    ap.add_argument("--refresh", type=int, default=15, help="giay giua cac lan export (voi --live)")
    ap.add_argument("--export-timeout", type=int, default=20)
    a = ap.parse_args()
    if a.live:
        threading.Thread(target=refresh_loop, args=(a.refresh, a.export_timeout), daemon=True).start()
        print(f"[i] LIVE: tu export moi ~{a.refresh}s")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"[i] Mo trinh duyet: http://127.0.0.1:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[i] Dung.")


if __name__ == "__main__":
    main()
