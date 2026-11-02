# Đăng ký nhận bản tin / Shared digest subscriptions

Bot tạo một bản tin cho mỗi lượt chạy rồi gửi lại nội dung đó cho mọi người nhận.
Workers chỉ xử lý đăng ký, không gọi Gemini. GitHub Actions vẫn chạy theo lịch
07:17 giờ Việt Nam; thời điểm thực tế có thể trễ do lịch của GitHub Actions.

## 1. Tạo Worker và D1

Cần Node.js 24+, npm và một tài khoản Cloudflare. Từ thư mục `worker`:

```powershell
npm ci
npx wrangler login
npx wrangler d1 create hackernews-subscribers
```

Thay `REPLACE_WITH_D1_DATABASE_ID` trong `worker/wrangler.jsonc` bằng ID vừa tạo.
Không cần domain riêng: Worker sử dụng địa chỉ HTTPS `workers.dev`.

```powershell
npx wrangler d1 migrations apply hackernews-subscribers --remote
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put SUBSCRIBER_API_TOKEN
npm run deploy
```

- `TELEGRAM_BOT_TOKEN`: token bot đang gửi bản tin.
- `TELEGRAM_WEBHOOK_SECRET`: chuỗi ngẫu nhiên riêng, tối thiểu 32 ký tự; chỉ dùng
  chữ, số, `_`, `-` để tương thích `setWebhook`.
- `SUBSCRIBER_API_TOKEN`: chuỗi ngẫu nhiên khác, tối thiểu 32 ký tự; dùng chung
  giữa Worker và workflow, không phải Cloudflare API token.
- Tạo giá trị ngẫu nhiên bằng trình quản lý mật khẩu; không đưa secret vào Git,
  ảnh chụp hoặc lệnh có thể lưu trong lịch sử terminal. Lệnh `secret put` hỏi giá trị.

## 2. Đăng ký Telegram webhook

Chạy đoạn PowerShell sau. Nhập token và secret qua lời nhắc, không đặt trực tiếp
vào lịch sử lệnh. Sử dụng cùng webhook secret đã lưu ở Worker.

```powershell
$botCredential = Read-Host 'Telegram bot token' -AsSecureString
$hookCredential = Read-Host 'Webhook secret' -AsSecureString
$workerBase = (Read-Host 'Worker HTTPS URL, without trailing slash').TrimEnd('/')
$botToken = [System.Net.NetworkCredential]::new('', $botCredential).Password
$hookSecret = [System.Net.NetworkCredential]::new('', $hookCredential).Password
try {
    $payload = @{
        url = "$workerBase/webhook"
        secret_token = $hookSecret
        allowed_updates = @('message')
        drop_pending_updates = $false
    } | ConvertTo-Json
    try {
        $result = Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$botToken/setWebhook" -ContentType 'application/json' -Body $payload -ErrorAction Stop
        Write-Output "Webhook registered: $($result.ok)"
    } catch { throw 'Webhook registration failed; check the token and Worker URL. Do not share raw request errors.' }
} finally {
    Remove-Variable botToken, hookSecret, botCredential, hookCredential, payload -ErrorAction SilentlyContinue
}
```

Bot chỉ có một webhook; thao tác này thay thế webhook cũ nếu có. Không chạy
`getUpdates`/polling với cùng bot khi webhook đang hoạt động.

## 3. Cấu hình GitHub Actions

Trong **Settings → Secrets and variables → Actions**, thêm repository secrets:

| Secret | Giá trị |
|---|---|
| `SUBSCRIBER_API_URL` | URL gốc của Worker, ví dụ `https://hackernews-subscriptions.example.workers.dev`, không thêm `/webhook` |
| `SUBSCRIBER_API_TOKEN` | Cùng giá trị đã lưu trong Worker |
| `TELEGRAM_BOT_TOKEN` | Giữ token bot hiện tại |
| `GEMINI_API_KEY` | Giữ khóa hiện tại |
| `TELEGRAM_CHAT_ID` | Tùy chọn: địa chỉ cố định hiện tại vẫn nhận bản tin |

URL API phải là HTTPS, không chứa thông tin đăng nhập, query hoặc fragment.
Thiếu một trong hai cấu hình `SUBSCRIBER_API_*` sẽ dừng job. Khi cả hai không
được cấu hình, bot dùng chế độ cũ và cần `TELEGRAM_CHAT_ID`.

Nếu bật API nhưng API lỗi, job dừng trước bước AI, không âm thầm bỏ danh sách
đăng ký. Nếu danh sách rỗng và không có chat cố định, job kết thúc mà không gọi AI.

## 4. Kiểm tra trước khi chia sẻ

1. Dùng tài khoản thử mở bot và gửi `/start`: nhận xác nhận đăng ký.
2. Gửi lại `/start`: không tạo trùng. Gửi `/stop`, rồi `/start` để kiểm tra hủy/đăng ký lại.
3. Chạy thủ công **Daily Hacker News Digest** một lần. Kiểm tra người thử và
   địa chỉ cố định nhận cùng bản tin, mỗi địa chỉ chỉ một lần, và log có tổng
   `successful`, `skipped`, `failed`.
4. Dùng tài khoản thứ hai đăng ký rồi chặn bot: lượt gửi tiếp theo phải bỏ qua
   đăng ký đó và vẫn gửi cho tài khoản thứ nhất.
5. Thử `/stop` trên tài khoản không phải `TELEGRAM_CHAT_ID`: không nhận ở lượt tiếp theo.

Chạy test local, không cần tài khoản Cloudflare hoặc token thật:

```powershell
# Từ root repository, sau khi cài requirements.txt
python -m pytest -q
# Từ thư mục worker
npm ci
npm test
npm run typecheck
npm run build
```

Worker tests chạy SQL thật trên SQLite cục bộ bằng Node, không gọi Telegram hoặc
D1 production. `npm run build` chỉ kiểm tra đóng gói, không triển khai.
`python -m src.main --dry-run` không đọc/sửa đăng ký và không gửi Telegram,
nhưng vẫn lấy bài và có thể gọi Gemini như chế độ dry-run trước đây.

## Hành vi và giới hạn

- Bất kỳ ai cũng được đăng ký qua chat riêng; `/start` trong nhóm không đăng ký nhóm.
- Người đăng ký mới chờ lượt gửi tiếp theo; `/start` không tạo hoặc gửi bản tin ngay.
- Worker lưu cả `last_update_id` và `last_message_id`, dùng thứ tự tin nhắn trong
  chat để bỏ qua lệnh cũ/trùng. Cách này xử lý được trường hợp Telegram cấp lại
  `update_id` nhỏ hơn sau thời gian không có update.
- `/stop` chỉ hủy đăng ký trong D1. Nếu địa chỉ vẫn nằm trong `TELEGRAM_CHAT_ID`,
  phải xóa cấu hình cố định để dừng nhận hoàn toàn.
- Danh sách được đọc trước khi tạo bản tin. Lệnh hủy khi đang gửi có hiệu lực
  ở lượt tiếp theo; phân trang không phải ảnh chụp giao dịch của toàn bộ D1.
- Gửi tuần tự, tối thiểu một giây giữa các yêu cầu, tối đa ba lần thử/yêu cầu,
  tối đa 120 giây chờ/người. Chỉ lỗi bot bị chặn hoặc người dùng đã bị xóa mới
  vô hiệu hóa đăng ký; lỗi khác làm job thất bại sau khi thử các người còn lại.
- Concurrency ngăn các lượt gửi chạy đồng thời. Không có tự chạy lại toàn job.
  Chạy lại thủ công vẫn tạo bản tin mới và có thể gửi trùng; retry sau timeout
  cũng có thể gửi trùng vì Telegram không hỗ trợ khóa idempotency cho sendMessage.
- Theo dõi log workflow và Cloudflare D1/Workers usage trong dashboard. Gói miễn phí
  có hạn mức; không bật paid broadcast của Telegram hay tự chuyển sang gói trả phí.
- API nội bộ dùng `Authorization: Bearer <SUBSCRIBER_API_TOKEN>`. `GET /subscribers`
  trả `{subscribers: [{chat_id, version}], next_cursor}`; gửi `?cursor=...` để đọc
  tiếp, tối đa 100 bản ghi/trang. `POST /subscribers/disable` nhận `{chat_id, version}`
  và chỉ hủy khi phiên bản vẫn khớp. Không công khai danh sách người nhận.

## Tắt tính năng / rollback

Xóa cả hai GitHub secrets `SUBSCRIBER_API_URL` và `SUBSCRIBER_API_TOKEN`, giữ hoặc
khôi phục `TELEGRAM_CHAT_ID` để quay về gửi cố định. Gỡ webhook bằng `deleteWebhook`
qua Telegram Bot API nếu muốn ngừng nhận lệnh; không cần xóa D1. Các lệnh đăng ký
còn hoạt động nếu chỉ tắt API trong workflow, nên thông báo cho người dùng trước.

Tài liệu chính thức: [D1 migrations](https://developers.cloudflare.com/d1/reference/migrations/),
[Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/),
[Telegram setWebhook](https://core.telegram.org/bots/api#setwebhook).
