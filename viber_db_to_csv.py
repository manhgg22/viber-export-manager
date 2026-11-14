#!/usr/bin/env python3
"""
viber_db_to_csv.py - Doc viber_export.db (do ViberPC-Export tao ra) -> CSV chuan.

Ban Viber moi luu NOI DUNG TIN trong bang Events.Body (khong co bang Messages rieng),
nen bo doc goc cua cong cu bi loi. Script nay doc thang Events + Contact + ChatInfo.

Ra CSV: DateTime, ChatID, Contact, Direction, MsgType, Message
(cung dinh dang viber_process.py doc duoc).

  python viber_db_to_csv.py vendor/ViberPC-Export/export/viber_export.db -o live_from_db.csv
"""
import argparse
import csv
import re
import sqlite3
from datetime import datetime, timezone

# Loai bo cac ky tu dinh huong vo hinh trong ten (U+2066..2069, U+200E/F)
_INVIS = re.compile(r"[⁦-⁩‎‏]")

# MessageType pho bien cua Viber (tuong doi; con lai gan nhan chung)
MT = {0: "text", 1: "text", 2: "image", 3: "video", 4: "sticker", 5: "location",
      6: "contact", 7: "file", 8: "url", 9: "rich", 10: "voice", 11: "system"}


def clean(s):
    return _INVIS.sub("", s).strip() if isinstance(s, str) else s


def ts(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OverflowError, OSError):
        return ""


def load_maps(c):
    contacts = {}
    for r in c.execute("SELECT ContactID, Name, ClientName, Number FROM Contact"):
        name = clean(r["Name"]) or clean(r["ClientName"]) or clean(r["Number"]) or f"#{r['ContactID']}"
        contacts[r["ContactID"]] = name
    chats = {}
    for r in c.execute("SELECT * FROM ChatInfo"):
        d = dict(r)
        nm = clean(d.get("Name") or "")
        if not nm and d.get("PGTabLine"):
            nm = clean(d["PGTabLine"])
        chats[d["ChatID"]] = nm  # co the rong -> xu ly sau
    # thanh vien moi chat (de suy ten chat 1-1)
    rel = {}
    try:
        for r in c.execute("SELECT ChatID, ContactID FROM ChatRelation"):
            rel.setdefault(r["ChatID"], []).append(r["ContactID"])
    except sqlite3.OperationalError:
        pass
    return contacts, chats, rel


def chat_title(cid, chats, rel, contacts, self_id):
    nm = chats.get(cid, "")
    if nm:
        return nm
    members = [m for m in rel.get(cid, []) if m != self_id]
    if len(members) == 1:
        return contacts.get(members[0], f"Chat {cid}")
    if members:
        return ", ".join(contacts.get(m, f"#{m}") for m in members[:3])
    return f"Chat {cid}"


def run(db, out):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    contacts, chats, rel = load_maps(c)
    # self = tai khoan co so dien thoai (ContactFlags co bit "self"); don gian: ContactID nho nhat co Number
    self_id = 1
    for r in c.execute("SELECT ContactID FROM Contact WHERE Number IS NOT NULL ORDER BY ContactID LIMIT 1"):
        self_id = r["ContactID"]

    rows = []
    for r in c.execute("SELECT EventID,TimeStamp,Direction,Type,ChatID,ContactID,MessageType,Body,PayloadPath "
                       "FROM Events ORDER BY TimeStamp"):
        d = dict(r)
        body = d.get("Body") or ""
        mtype = MT.get(d.get("MessageType"), f"type{d.get('MessageType')}")
        if not body:
            body = f"[{mtype}]" + (f" {clean(d['PayloadPath'])}" if d.get("PayloadPath") else "")
        rows.append({
            "DateTime": ts(d["TimeStamp"]),
            "ChatID": chat_title(d["ChatID"], chats, rel, contacts, self_id),
            "Contact": contacts.get(d["ContactID"], f"#{d['ContactID']}"),
            "Direction": "OUT" if d.get("Direction") == 1 else "IN",
            "MsgType": mtype,
            "Message": body,
        })
    c.close()

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["DateTime", "ChatID", "Contact", "Direction", "MsgType", "Message"])
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] {len(rows)} tin nhan -> {out}")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("-o", "--out", default="live_from_db.csv")
    a = ap.parse_args()
    run(a.db, a.out)


if __name__ == "__main__":
    main()
