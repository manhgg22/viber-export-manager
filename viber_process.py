#!/usr/bin/env python3
"""
viber_process.py - Bien viber_export.json thanh du lieu quan tri cho C-level.

Dau vao : viber_export.json  (do ViberPC-Export / viber-export-macos tao ra)
Dau ra  (cung thu muc --out, mac dinh ./processed):
  - groups_summary.csv : moi group/chat 1 dong (so tin, thanh vien, khoang thoi gian, nguoi gui nhieu nhat)
  - messages_all.csv   : toan bo tin nhan dang bang phang (de loc / dua cho AI)
  - overview.md        : ban tom tat gon cho C-level (va de dan vao Grok)

Khong goi mang, khong gui du lieu di dau. Chi doc 1 file JSON cuc bo.

Dung:
  python viber_process.py path/to/viber_export.json
  python viber_process.py export/viber_export.json --out processed --only group,community
"""
import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def name_of(doc, cid):
    """Ten hien thi cua mot ContactID."""
    if cid is None:
        return ""
    c = doc.get("contacts", {}).get(str(cid))
    if c:
        return c.get("name") or c.get("number") or f"#{cid}"
    if cid in set(doc.get("self", {}).get("contactIds", [])):
        return doc.get("self", {}).get("name") or "Toi"
    return f"#{cid}"


def ts_to_str(ms):
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OverflowError, OSError):
        return ""


def message_text(m):
    """Mot dong text dai dien cho moi loai tin nhan."""
    kind = m.get("kind", "")
    if m.get("text"):
        return m["text"]
    if m.get("caption"):
        return m["caption"]
    if kind == "image":
        return "[hinh anh]"
    if kind == "video":
        return "[video]"
    if kind == "voice":
        return "[tin nhan thoai]"
    if kind == "file":
        nm = (m.get("media") or {}).get("name") or ""
        return f"[file] {nm}".strip()
    if kind == "sticker":
        return "[sticker]"
    if kind == "location":
        return "[vi tri]"
    if kind == "contact":
        return "[danh thiep]"
    if kind == "call":
        return "[cuoc goi]"
    return f"[{kind}]" if kind else ""


def iter_messages(chat):
    for m in chat.get("messages", []):
        yield m


def process(doc, only=None):
    """Tra ve (summary_rows, flat_rows)."""
    summary, flat = [], []
    for chat in doc.get("chats", []):
        ctype = chat.get("type", "")
        if only and ctype not in only:
            continue
        title = chat.get("title", "")
        msgs = list(iter_messages(chat))
        times = [m.get("timestamp") for m in msgs if m.get("timestamp")]
        senders = Counter()
        for m in msgs:
            if m.get("kind") == "call":
                continue
            senders[name_of(doc, m.get("authorId"))] += 1
        top = senders.most_common(1)
        summary.append({
            "chat_id": chat.get("id"),
            "title": title,
            "type": ctype,
            "messages": len(msgs),
            "participants": len(chat.get("memberIds", [])) + 1,  # + chinh minh
            "first": ts_to_str(min(times)) if times else "",
            "last": ts_to_str(max(times)) if times else "",
            "top_sender": top[0][0] if top else "",
            "top_sender_count": top[0][1] if top else 0,
        })
        for m in msgs:
            flat.append({
                "chat_title": title,
                "chat_type": ctype,
                "datetime_utc": ts_to_str(m.get("timestamp")),
                "sender": name_of(doc, m.get("authorId")) if m.get("kind") != "call" else "",
                "outgoing": 1 if m.get("outgoing") else 0,
                "kind": m.get("kind", ""),
                "text": message_text(m),
            })
    summary.sort(key=lambda r: r["messages"], reverse=True)
    flat.sort(key=lambda r: (r["chat_title"], r["datetime_utc"]))
    return summary, flat


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_overview(path, doc, summary, flat):
    total_msgs = sum(s["messages"] for s in summary)
    groups = [s for s in summary if s["type"] in ("group", "community")]
    lines = []
    lines.append("# Tong quan tin nhan Viber\n")
    lines.append(f"- Xuat luc: {doc.get('exportedAt', '?')}")
    lines.append(f"- So cuoc tro chuyen: **{len(summary)}**  "
                 f"(group/community: **{len(groups)}**)")
    lines.append(f"- Tong tin nhan: **{total_msgs}**\n")
    lines.append("## Cac group/community theo luu luong\n")
    lines.append("| Group | Loai | Tin nhan | Thanh vien | Gan nhat | Nguoi gui nhieu nhat |")
    lines.append("|---|---|---:|---:|---|---|")
    for s in summary:
        if s["type"] == "direct":
            continue
        lines.append(f"| {s['title']} | {s['type']} | {s['messages']} | "
                     f"{s['participants']} | {s['last']} | {s['top_sender']} ({s['top_sender_count']}) |")
    lines.append("\n> File `messages_all.csv` chua toan bo tin nhan dang bang, "
                 "san sang dua cho AI (Grok) phan tich / phan loai theo du an.")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def process_mac_csv(path, only=None):
    """Doc CSV cua viber-export-macos (cot: DateTime, ChatID, Contact, Direction, MsgType, Message).
    Tra ve (summary_rows, flat_rows) cung dinh dang voi process()."""
    import collections
    by_chat = collections.OrderedDict()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            cid = r.get("ChatID", "")
            by_chat.setdefault(cid, []).append(r)

    summary, flat = [], []
    for cid, rows in by_chat.items():
        contacts = set(x.get("Contact", "") for x in rows if x.get("Direction", "").upper() != "OUT")
        ctype = "group" if len(contacts) > 1 else "direct"
        if only and ctype not in only:
            continue
        # ChatID tu luong live chinh la ten group (chu); tu engine Mac thuong la so.
        if cid and not str(cid).isdigit():
            title = cid
        else:
            nm = sorted(c for c in contacts if c)[:1]
            title = (nm[0] if nm else "") + (f" (chat {cid})" if ctype == "group" else "")
        if not title:
            title = f"chat {cid}"
        senders = Counter(x.get("Contact", "") for x in rows)
        times = [x.get("DateTime", "") for x in rows if x.get("DateTime")]
        top = senders.most_common(1)
        summary.append({
            "chat_id": cid, "title": title, "type": ctype, "messages": len(rows),
            "participants": len(contacts) + 1,
            "first": min(times) if times else "", "last": max(times) if times else "",
            "top_sender": top[0][0] if top else "", "top_sender_count": top[0][1] if top else 0,
        })
        for x in rows:
            flat.append({
                "chat_title": title, "chat_type": ctype,
                "datetime_utc": x.get("DateTime", ""),
                "sender": x.get("Contact", ""),
                "outgoing": 1 if x.get("Direction", "").upper() == "OUT" else 0,
                "kind": x.get("MsgType", ""), "text": x.get("Message", ""),
            })
    summary.sort(key=lambda r: r["messages"], reverse=True)
    flat.sort(key=lambda r: (r["chat_title"], r["datetime_utc"]))
    return summary, flat


def main():
    ap = argparse.ArgumentParser(description="Xu ly export Viber (JSON Windows hoac CSV Mac) cho C-level")
    ap.add_argument("input", help="viber_export.json (Windows) hoac viber_export.csv (Mac)")
    ap.add_argument("--out", default="processed", help="thu muc ket qua (mac dinh ./processed)")
    ap.add_argument("--only", default=None,
                    help="chi lay cac loai, phan cach dau phay: group,direct (community: Windows)")
    a = ap.parse_args()

    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    if a.input.lower().endswith(".csv"):
        doc = {"exportedAt": "(Mac CSV)", "chats": []}
        summary, flat = process_mac_csv(a.input, only)
    else:
        doc = load(a.input)
        summary, flat = process(doc, only)

    os.makedirs(a.out, exist_ok=True)
    write_csv(os.path.join(a.out, "groups_summary.csv"), summary,
              ["chat_id", "title", "type", "messages", "participants",
               "first", "last", "top_sender", "top_sender_count"])
    write_csv(os.path.join(a.out, "messages_all.csv"), flat,
              ["chat_title", "chat_type", "datetime_utc", "sender", "outgoing", "kind", "text"])
    write_overview(os.path.join(a.out, "overview.md"), doc, summary, flat)

    print(f"[OK] {len(summary)} cuoc tro chuyen, {len(flat)} tin nhan")
    print(f"     -> {os.path.join(a.out, 'groups_summary.csv')}")
    print(f"     -> {os.path.join(a.out, 'messages_all.csv')}")
    print(f"     -> {os.path.join(a.out, 'overview.md')}")


if __name__ == "__main__":
    main()
