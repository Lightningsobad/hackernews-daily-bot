# ⚡️ Hacker News AI & Programming Daily Telegram Digest Bot

<p align="center">
  <a href="README.md">English</a> | <strong>Tiếng Việt</strong>
</p>

Một ứng dụng tự động hoá gọn nhẹ, chạy định kỳ hàng ngày hoàn toàn miễn phí trên **GitHub Actions** (chi phí server = 0đ) nhằm:
1. Thu thập các bài viết nổi bật nhất về chủ đề **Trí tuệ nhân tạo (AI)** và **Lập trình (Programming)** trên Hacker News trong vòng 24 giờ qua.
2. Tải nội dung bài viết và sử dụng **Google Gemini AI** để đọc hiểu, tóm tắt thành 2–3 gạch đầu dòng súc tích bằng tiếng Việt.
3. Đóng gói và gửi bản tin tổng hợp đẹp mắt vào kênh hoặc nhóm Telegram của bạn vào 07:00 sáng mỗi ngày.

---

## 🚀 Hướng dẫn Lấy các Thông tin Bí mật (Secrets)

### 1. `TELEGRAM_BOT_TOKEN`
1. Mở Telegram, tìm kiếm bot chính thức **[@BotFather](https://t.me/BotFather)**.
2. Gõ lệnh `/newbot`, đặt tên và username cho bot theo hướng dẫn.
3. `@BotFather` sẽ gửi cho bạn một chuỗi token dạng: `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`.

### 2. `TELEGRAM_CHAT_ID`
- **Gửi vào Kênh (Channel)** hoặc **Nhóm (Group)**:
  1. Thêm bot bạn vừa tạo vào Kênh/Nhóm với quyền **Administrator** (quyền Post Messages).
  2. Gửi một tin nhắn bất kỳ vào kênh.
  3. Để lấy ID kênh: Bạn có thể thêm bot **[@userinfobot](https://t.me/userinfobot)** hoặc **[@getmyid_bot](https://t.me/getmyid_bot)** vào kênh để xem ID (thường bắt đầu bằng `-100...`, ví dụ `-1001234567890`).
- **Gửi vào Chat Cá nhân**:
  1. Mở chat với bot bạn vừa tạo, bấm `/start`.
  2. Mở chat với **[@userinfobot](https://t.me/userinfobot)**, bot sẽ trả về `Id` cá nhân của bạn (dạng số nguyên dương, ví dụ `987654321`).

### 3. `GEMINI_API_KEY`
1. Truy cập [Google AI Studio](https://aistudio.google.com/).
2. Đăng nhập bằng tài khoản Google.
3. Chọn **Get API Key** -> **Create API Key in new project**.
4. Sao chép API key được cấp (hoàn toàn miễn phí, hạn mức 15 requests/phút).

---

## ⚙️ Cấu hình trên GitHub (Để chạy tự động)

Sau khi đẩy mã nguồn lên GitHub repository của bạn:
1. Truy cập vào GitHub Repo -> Chọn tab **Settings**.
2. Ở thanh bên trái, chọn **Secrets and variables** -> Chọn **Actions**.
3. Bấm **New repository secret** và thêm lần lượt 3 biến:
   - `TELEGRAM_BOT_TOKEN`: Token lấy từ BotFather.
   - `TELEGRAM_CHAT_ID`: ID kênh/nhóm hoặc chat cá nhân của bạn.
   - `GEMINI_API_KEY`: API Key lấy từ Google AI Studio.
4. *(Tùy chọn)* Nếu muốn đổi model AI sang phiên bản khác (mặc định là `gemini-3.8-flash`), bạn có thể vào tab **Variables** bên cạnh -> Thêm variable `GEMINI_MODEL` (ví dụ `gemini-3.5-flash-lite`).

Bot sẽ tự động kích hoạt vào lúc **00:00 UTC (tức 07:00 sáng giờ Việt Nam)** mỗi ngày. Bạn cũng có thể kích hoạt chạy thử thủ công bất kỳ lúc nào bằng cách vào tab **Actions** trên GitHub -> Chọn workflow **Daily Hacker News Digest** -> Bấm **Run workflow**.

---

## 🛡️ Cơ chế Chống lỗi Model AI (Model Cascade)

Hệ thống được trang bị cơ chế tự động bảo vệ:
- Nếu model được cấu hình (`GEMINI_MODEL`) bị Google ngừng hỗ trợ (deprecated) hoặc trả về lỗi 404, bot sẽ tự động đảo qua danh sách model dự phòng:
  `gemini-3.8-flash` ➡️ `gemini-3.5-flash-lite`.
- Nếu toàn bộ dịch vụ AI gặp sự cố ngắt kết nối, bot **vẫn gửi bản tin đầy đủ** với tiêu đề, điểm vote, link bài gốc và link thảo luận kèm dòng chú thích dự phòng, đảm bảo bạn không bao giờ bị gián đoạn bản tin buổi sáng.

---

## 💻 Hướng dẫn Chạy Thử nghiệm tại Local

### 1. Chuẩn bị môi trường
```bash
# Khởi tạo môi trường ảo Python
python -m venv .venv

# Kích hoạt môi trường ảo:
# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1
# Trên Linux/macOS:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Thiết lập file cấu hình Local
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```
Mở file `.env` và điền token/key của bạn. *(Lưu ý: File này đã được `.gitignore` chặn nên sẽ không bị commit)*.

### 3. Chạy thử nghiệm
- **Chạy chế độ thử nghiệm (Dry Run)**: Thu thập tin thật, gọi AI tóm tắt thật và in bản tin ra terminal, **không gửi tin nhắn đến Telegram**:
  ```bash
  python -m src.main --dry-run
  ```
- **Chạy chế độ thật**: Gửi trực tiếp bản tin vào Telegram:
  ```bash
  python -m src.main
  ```

### 4. Chạy bộ kiểm thử (Unit Tests)
```bash
pytest -v
```

