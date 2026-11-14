# Viber Export Manager

Lấy tin nhắn (kể cả group) từ **Viber Desktop** trên máy tính, xuất ra CSV + báo cáo,
và xem **gần real-time** trên một trang web. Dành cho việc quản lý / phân tích tin nhắn
của **chính bạn** (ví dụ: tổng hợp nhiều group công việc để báo cáo, đưa cho AI phân tích).

> **Mọi thứ chạy cục bộ trên máy bạn. Không gửi dữ liệu đi đâu.**

---

## Làm được gì

- Giải mã database Viber Desktop (đã mã hoá) **qua chính engine của Viber** (Frida) — không cần tìm key.
- Xuất tin nhắn (text, ảnh/video/voice path, group, 1-1) ra **CSV** chuẩn.
- Sinh **báo cáo tổng quan** cho quản lý: mỗi group bao nhiêu tin, ai gửi nhiều nhất, mốc thời gian.
- **Trang web** tự cập nhật xem tin mới (gần real-time, có nút "Làm mới ngay").
- (Tuỳ chọn) **Server nhận webhook** cho hướng Android forwarder — real-time thật sự.

## Nó KHÔNG làm được (giới hạn của Viber, không phải của tool)

- **Không lấy được tin cũ chưa đồng bộ về máy này.** Viber Desktop chỉ chứa lịch sử nó đã
  đồng bộ từ điện thoại kể từ lúc được liên kết. Tin trước đó nằm trong điện thoại.
- **Không real-time tức thì** trên hướng Desktop: mỗi lần export mất ~30–90s (Frida gắn vào Viber).
  Muốn tức thì → dùng hướng Android (xem cuối README).
- Bot API của Viber **không** đọc được group chat — nên không dùng được cách đó.

---

## Yêu cầu

- **Windows 10/11** (hướng chính), **macOS** (xem mục Mac), hoặc **Linux** (xem mục Linux — thử nghiệm).
- **Python 3.10+** — https://www.python.org/downloads/ (khi cài nhớ tick *Add to PATH*).
- **Viber Desktop** đã cài, **đang đăng nhập**, và đang chạy.

---

## Cài & chạy trên WINDOWS (3 bước)

```bat
:: 1) Cài thư viện (1 lần) — cài Frida
install.bat

:: 2) Mở Viber Desktop và đăng nhập.

:: 3) Export + ra báo cáo (1 lệnh)
viber_sync.bat
```

Kết quả nằm trong thư mục này:

| File | Nội dung |
|------|----------|
| `live_from_db.csv` | Toàn bộ tin, dạng bảng: DateTime, ChatID, Contact, Direction, MsgType, Message |
| `processed_real/overview.md` | Tổng quan các group cho quản lý |
| `processed_real/messages_all.csv` | Bảng phẳng, sẵn sàng đưa cho AI (Grok/Claude/ChatGPT) phân tích |

> Khi chạy, nếu báo *"no activity / Export not created"*: hãy **bấm chuyển qua lại vài cuộc trò chuyện**
> trong Viber để Viber đọc database → tool mới chộp được. Đây là cơ chế của Frida.

### Trang web xem gần real-time

```bat
:: Chỉ xem + nút "Làm mới ngay"
python viber_web.py --port 17653

:: Hoặc TỰ ĐỘNG export lặp (gần real-time, ~30–90s/lần)
python viber_web.py --port 17653 --live --refresh 5 --export-timeout 30
```

Mở trình duyệt: **http://127.0.0.1:17653**

### Tự động chạy ngầm (không cần bấm)

Dùng Task Scheduler của Windows để chạy `viber_sync.bat` định kỳ:

```powershell
schtasks /create /tn "ViberSync" /tr "%CD%\viber_sync.bat" /sc minute /mo 10 /f
```

---

## Cài & chạy trên LINUX (thử nghiệm)

Viber for Linux cũng là ứng dụng **Qt** giống bản Windows, nên dùng **chung engine Frida**.
Chỉ khác tên module/symbol của Qt — engine đã tự nhận cả hai kiểu (Windows & Linux).

```bash
# 1) Cài Frida (1 lần)
chmod +x install.sh viber_sync.sh
./install.sh

# 2) Mở Viber Desktop và đăng nhập.

# 3) Export + ra báo cáo (1 lệnh)
./viber_sync.sh
```

Kết quả giống hệt Windows: `live_from_db.csv`, `processed_real/overview.md`,
`processed_real/messages_all.csv`. Trang web và server webhook (`viber_web.py`,
`viber_ingest_server.py`) chạy y như trên Windows (`python3 viber_web.py --port 17653`).

Tự động chạy ngầm bằng **cron** (thay cho Task Scheduler):

```bash
# mỗi 10 phút
( crontab -l 2>/dev/null; echo "*/10 * * * * cd $PWD && ./viber_sync.sh >> viber_sync.log 2>&1" ) | crontab -
```

> ⚠️ **Phần Linux chưa được test trên máy Linux thật.** Engine bám vào ký hiệu nội bộ của Qt.
> Nếu thấy `symbol not found` hoặc file export rỗng:
> - Viber Linux có thể dùng **Qt5** (bản Windows dùng Qt6). Cách đọc chuỗi (QString) trong engine
>   viết theo bố cục **Qt6**; với Qt5 có thể cần chỉnh. Mở issue kèm dòng báo lỗi (nó in ra tên module
>   Qt tìm được) để mình cập nhật.
> - Chạy cần quyền gắn tiến trình: nếu bị chặn `ptrace`, chạy với `sudo ./viber_sync.sh`, hoặc tạm thời
>   `echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope`.
> - Bản **Snap/Flatpak** chạy trong sandbox — Frida khó gắn vào; nên dùng bản `.deb`/AppImage thường.

---

## Cài & chạy trên macOS

Engine Windows không chạy trên Mac. Dùng engine riêng cho Mac:

```bash
# 1) Cài Xcode Command Line Tools
xcode-select --install

# 2) Tải engine Mac vào thư mục này
git clone https://github.com/Anastasia-D-Kravchenko/viber-export-macos.git

# 3) Chạy (nên thoát Viber trước)
chmod +x run_viber_export_mac.sh
./run_viber_export_mac.sh
```

Engine Mac xuất ra `viber_export.csv` (DateTime, ChatID, Contact, Direction, MsgType, Message),
`viber_process.py` đọc trực tiếp định dạng này.

> ⚠️ Phần Mac **chưa được test trên máy Mac thật** — cần chạy thử và báo lỗi nếu có.

---

## Các thành phần

| File | Vai trò | Tác giả |
|------|---------|---------|
| `viber_locate.py` | Dò vị trí viber.db, báo đã mã hoá chưa (Win + Mac) | repo này |
| `viber_db_to_csv.py` | Đọc `viber_export.db` → CSV. **Đọc `Events.Body`** (xem ghi chú) | repo này |
| `viber_process.py` | CSV (Win hoặc Mac) → báo cáo overview + bảng cho AI | repo này |
| `viber_web.py` | Trang web xem gần real-time + nút làm mới + loop tự export | repo này |
| `viber_ingest_server.py` | Server webhook nhận tin từ Android forwarder (real-time) | repo này |
| `viber_sync.bat` | 1 lệnh (Windows): export → CSV → báo cáo | repo này |
| `viber_sync.sh` | 1 lệnh (Linux): export → CSV → báo cáo | repo này |
| `install.bat` / `install.sh` | Cài Frida (Windows / Linux-macOS) | repo này |
| `run_viber_export_mac.sh` | Bản bọc cho macOS (engine lldb riêng) | repo này |
| `vendor/ViberPC-Export/` | Engine giải mã Viber Desktop (Windows, Frida) | **GPL-3.0**, bên thứ ba |

### Ghi chú kỹ thuật quan trọng

Bản Viber Desktop mới **không còn bảng `Messages` riêng** — nội dung tin nằm trong bảng
**`Events.Body`**. Engine gốc (ViberPC-Export) tìm bảng `Messages` nên báo "missing", nhưng
dữ liệu vẫn được export đầy đủ trong `Events`. Vì vậy repo này dùng `viber_db_to_csv.py`
đọc thẳng `Events` + `Contact` + `ChatInfo` + `ChatRelation`, bỏ qua phần dựng JSON bị lỗi
của engine gốc. Thấy dòng `Messages: missing` khi export là **bình thường**.

---

## Real-time thật sự — hướng Android (tuỳ chọn)

Hướng Desktop chỉ *gần* real-time. Muốn tin vào **tức thì**:

1. Một máy **Android** đăng nhập Viber, cài app notification-forwarder
   (ví dụ `YipKean/NotificationForwarder`).
2. Chạy server nhận: `python viber_ingest_server.py --port 17653 --out live_from_db.csv`
3. Trỏ webhook của app tới `http://<IP-máy-chạy-server>:17653/hook`.
4. Bật thông báo cho các group cần theo dõi.

Mỗi tin mới sẽ được đẩy vào `live_from_db.csv` ngay lập tức, rồi `viber_process.py` xử lý.

---

## Xử lý sự cố

| Triệu chứng | Cách khắc phục |
|-------------|----------------|
| `Viber is not running` | Mở Viber Desktop và đăng nhập trước khi chạy. |
| `Export not created / no activity` | Bấm chuyển qua lại vài chat trong Viber trong lúc tool đang chờ. |
| `Messages: missing` | **Bình thường** — nội dung ở `Events.Body`, vẫn lấy đủ. |
| Export rất chậm (~90s) | Máy tải nặng → Frida gắn chậm. Đóng bớt ứng dụng, hoặc chấp nhận độ trễ. |
| Cổng đã bị chiếm | Đổi `--port` sang cổng khác đang trống. |
| Antivirus cảnh báo | Frida bị gắn cờ do can thiệp tiến trình; cho phép nếu bạn tin tưởng. |
| Viber cập nhật lớn làm hỏng | Engine bám vào ký hiệu nội bộ Qt của Viber; có thể cần cập nhật lại khi Viber đổi. |
| `symbol not found` (Linux/Mac) | Qt khác phiên bản. Dòng lỗi in ra tên module Qt tìm được — gửi vào issue. Linux có thể là Qt5. |
| `ptrace` bị chặn (Linux) | `sudo ./viber_sync.sh`, hoặc `echo 0 \| sudo tee /proc/sys/kernel/yama/ptrace_scope`. |

---

## ⚠️ Lưu ý pháp lý & đạo đức

- Chỉ dùng cho **tài khoản Viber của chính bạn, trên máy của bạn**.
- Công cụ **can thiệp vào tiến trình Viber** để giải mã DB → có thể **vi phạm Điều khoản dịch vụ
  của Viber**. Bạn tự chịu trách nhiệm.
- Tin nhắn group chứa dữ liệu của người khác (khách, đối tác). Nên chỉ xử lý group công việc của
  mình và cho thành viên biết dữ liệu được lưu/phân tích. Trước khi đưa cho AI đám mây, cân nhắc
  che bớt thông tin nhạy cảm.

## Giấy phép

- Mã trong repo này (các file `viber_*.py`, `*.bat`, `*.sh`): **MIT** — xem `LICENSE`.
- `vendor/ViberPC-Export/`: **GPL-3.0**, giữ nguyên giấy phép của tác giả gốc
  (xem `vendor/ViberPC-Export/LICENSE`).
