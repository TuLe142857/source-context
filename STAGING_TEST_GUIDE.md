# Chuẩn bị môi trường staging và kiểm thử khói

Dùng máy local, máy ảo hoặc máy chủ staging riêng. Không trỏ cấu hình staging
đến database, object storage hoặc GitHub App production. Hướng dẫn này chạy
image dev với volume staging riêng, chỉ mở các cổng trên localhost; GitHub cần
một HTTPS tunnel tạm thời để gửi webhook vào máy staging.

## Các file và cấu hình cần có

| File/cấu hình | Mục đích | Bạn cần làm gì |
|---|---|---|
| `.env.staging` | Cấu hình staging và credential riêng | Tạo từ `.env.example`, rồi sửa các giá trị theo mục 1. Không commit hoặc gửi file này qua chat. |
| `docker-compose.staging.yml` | Tách volume chứa repository clone khỏi môi trường khác | File đã có trong project; không cần sửa. Lệnh chạy phải có đủ ba file Compose như các mục dưới. |
| GitHub App thử nghiệm | Cấp quyền đọc repository và gửi webhook staging | Tạo riêng trong GitHub Developer Settings; cấu hình theo mục 4. Đây là cấu hình trên GitHub, không phải file trong repository. |
| HTTPS tunnel tạm | Cho GitHub gửi webhook đến máy local | Khởi chạy lệnh ở mục 4 trong một terminal riêng; không cần tạo file cấu hình tunnel. |

Không lưu file private key `.pem` trong repository. Tạo key trong GitHub, giữ file
ở nơi an toàn bên ngoài project, rồi đưa nội dung vào biến
`SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY` trong `.env.staging` với xuống dòng
được biểu diễn bằng `\n`.

## 1. Tạo thông tin xác thực và cấu hình staging

Sao chép `.env.example` thành `.env.staging` ở thư mục gốc repository. File
`.env.staging` đã được gitignore:

```powershell
Copy-Item .env.example .env.staging
notepad .env.staging
```

Thay toàn bộ mật khẩu mẫu, API key và giá trị `changethis`; xóa mọi nội dung
giữ chỗ trong dấu ngoặc nhọn trước khi chạy Compose. Có thể tạo secret trong
terminal riêng bằng lệnh sau:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Chạy lệnh riêng cho application secret và từng thông tin xác thực dịch vụ;
không dùng lại giá trị mẫu. Tạo credential riêng cho Postgres, Neo4j, Redis và
MinIO. Mật khẩu Redis cần dùng ký tự an toàn cho URL vì nó được đưa vào
`SOURCE_CONTEXT_CELERY_BROKER_URL`.

Đặt ít nhất các giá trị sau. Giữ các thiết lập dịch vụ bắt buộc khác từ file
mẫu, nhưng thay credential mẫu của chúng:

```dotenv
SOURCE_CONTEXT_ENV_STATE=dev
SOURCE_CONTEXT_ENVIRONMENT=development
SOURCE_CONTEXT_DEBUG=false
SOURCE_CONTEXT_LOG_LEVEL=INFO
SOURCE_CONTEXT_SECRET_KEY=<secret mới, ngẫu nhiên>
SOURCE_CONTEXT_FRONTEND_URL=http://localhost:15173

SOURCE_CONTEXT_FRONTEND_PORT=15173
SOURCE_CONTEXT_BACKEND_PORT=18000
SOURCE_CONTEXT_POSTGRES_PORT=5432
SOURCE_CONTEXT_POSTGRES_HOST_PORT=15432
SOURCE_CONTEXT_NEO4J_HTTP_PORT=17474
SOURCE_CONTEXT_NEO4J_PORT=7687
SOURCE_CONTEXT_NEO4J_BOLT_HOST_PORT=17687
SOURCE_CONTEXT_REDIS_PORT=6379
SOURCE_CONTEXT_REDIS_HOST_PORT=16379
SOURCE_CONTEXT_MINIO_API_PORT=19000
SOURCE_CONTEXT_MINIO_CONSOLE_PORT=19001
SOURCE_CONTEXT_REDIS_INSIGHT_PORT=15540
SOURCE_CONTEXT_MAILHOG_SMTP_PORT=11025
SOURCE_CONTEXT_MAILHOG_HTTP_PORT=18025

SOURCE_CONTEXT_POSTGRES_DB=source_context_staging
SOURCE_CONTEXT_POSTGRES_USER=staging_user
SOURCE_CONTEXT_POSTGRES_PASSWORD=<mật khẩu staging riêng>
SOURCE_CONTEXT_REDIS_USER=staging_user
SOURCE_CONTEXT_REDIS_PASSWORD=<mật khẩu staging riêng, an toàn cho URL>
SOURCE_CONTEXT_CELERY_BROKER_URL=redis://staging_user:<cùng mật khẩu Redis>@redis:6379/0
SOURCE_CONTEXT_NEO4J_USER=neo4j
SOURCE_CONTEXT_NEO4J_PASSWORD=<mật khẩu staging riêng>
SOURCE_CONTEXT_MINIO_ROOT_USER=<tên người dùng staging riêng>
SOURCE_CONTEXT_MINIO_ROOT_PASSWORD=<mật khẩu staging riêng>

SOURCE_CONTEXT_SMTP_SERVER=mailhog
SOURCE_CONTEXT_SMTP_PORT=1025
SOURCE_CONTEXT_SMTP_USER=staging
SOURCE_CONTEXT_SMTP_PASSWORD=<giá trị staging không để trống>
SOURCE_CONTEXT_SMTP_SEND_MAIL_FROM=staging@example.invalid
SOURCE_CONTEXT_SMTP_USE_TLS=false

SOURCE_CONTEXT_GITHUB_APP_ID=<App ID của GitHub App thử nghiệm>
SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY=<PEM với ký tự xuống dòng đã escape>
GITHUB_WEBHOOK_SECRET=<secret thử nghiệm riêng>
VITE_GITHUB_APP_NAME=<slug của GitHub App thử nghiệm>

SOURCE_CONTEXT_OPENAI_API_KEY=<API key LLM staging>
SOURCE_CONTEXT_OPENAI_API_BASE_URL=https://api.openai.com/v1
SOURCE_CONTEXT_OPENAI_MODEL=gpt-4o-mini
SOURCE_CONTEXT_VOYAGE_API_KEY=<API key embedding staging>
SOURCE_CONTEXT_VOYAGE_EMBEDDING_MODEL=voyage-code-3
```

Các API key OpenAI-compatible và Voyage cần thiết để chạy thử toàn bộ pipeline
index. Có thể bỏ qua nếu chỉ kiểm tra xác thực webhook và tạo job; khi đó worker
sẽ thất bại ở bước gọi dịch vụ AI. Nên dùng repository nhỏ để hạn chế chi phí.

## 2. Kiểm tra cấu hình và khởi động các dịch vụ staging

Chạy lệnh từ thư mục gốc repository trong PowerShell. Tên Compose project riêng
giúp cách ly volume database dev; overlay staging cũng đặt tên riêng cho
volume chứa source code được clone.

```powershell
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging config --quiet
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging up -d --build
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging ps
```

Chờ Postgres, Neo4j, Redis, Qdrant và MinIO chuyển sang trạng thái healthy. Nếu
backend hoặc worker thoát, xem log bằng lệnh:

```powershell
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging logs --tail 100 backend celery-worker
```

Kiểm tra `http://localhost:18000/health` và mở giao diện tại
`http://localhost:15173`.

## 3. Áp dụng migration vào database staging

Chạy hai migration theo đúng thứ tự, chỉ dùng Compose project và file môi
trường staging:

```powershell
Get-Content backend/migrations/20261004_add_indexed_commit_sha.sql | docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
Get-Content backend/migrations/20261004_add_github_webhook_deliveries.sql | docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Hai script chỉ bổ sung schema và có thể chạy lại an toàn. Lưu kết quả chạy
thành công trong ghi chú staging.

## 4. Kết nối GitHub App thử nghiệm

Tạo GitHub App riêng cho staging; không dùng chung cấu hình webhook với
production. Cấp quyền repository **Contents: Read-only** và giữ Metadata ở
trạng thái được cấp. Đăng ký các sự kiện `push`, `installation` và
`installation_repositories`. Trong thời gian thử nghiệm, chọn **Only on this
account**. GitHub có hai trường riêng **Setup URL** và **Webhook URL**; điền
đúng URL tương ứng bên dưới.

Trong trang cài đặt tài khoản GitHub, mở **Settings → Developer settings →
GitHub Apps → New GitHub App**. Đặt tên nhận biết rõ đây là App staging. Sau khi
tạo App:

1. Sao chép **App ID** vào `SOURCE_CONTEXT_GITHUB_APP_ID`.
2. Trong phần private key, tạo và tải một key mới; chép nội dung PEM vào
   `SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY`, không chép file `.pem` vào project.
3. Trong **Repository permissions**, đặt **Contents** thành **Read-only**;
   Metadata cần được cấp để GitHub nhận diện repository.
4. Trong **Subscribe to events**, bật `push`, `installation` và
   `installation_repositories`.
5. Sao chép **Webhook secret** vào `GITHUB_WEBHOOK_SECRET`. Giá trị này phải
   giống hệt secret nhập ở GitHub App.
6. Sao chép slug từ URL cài đặt dạng `github.com/apps/<slug>` vào
   `VITE_GITHUB_APP_NAME`.

Đặt các giá trị này trong `.env.staging` trước khi chạy lần đầu. Nếu đã tạo
container rồi mới thay đổi file, cần tạo lại các container để chúng nhận biến
môi trường mới:

```powershell
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging up -d --force-recreate frontend backend celery-worker
```

Mở terminal khác và chạy HTTPS tunnel tạm thời đến backend staging. Ví dụ nếu
đã cài Cloudflare Tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:18000
```

Dùng HTTPS URL được in ra để đặt Webhook URL của GitHub App thành
`https://<tunnel-host>/api/v1/webhooks/github`; webhook secret phải khớp với
`GITHUB_WEBHOOK_SECRET`. Đặt Setup URL thành
`https://<tunnel-host>/api/v1/webhooks/setup`. Frontend vẫn chạy local; URL
redirect sau khi cài App lấy từ `SOURCE_CONTEXT_FRONTEND_URL`.

Quick Tunnel công khai URL trong khi tiến trình đang chạy và URL ngừng hoạt
động khi tiến trình kết thúc. Chỉ expose backend staging đã cách ly, chỉ dùng
credential và dữ liệu staging, rồi dừng tunnel sau khi thử. Tham khảo [hướng
dẫn đăng ký GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-github-app/registering-a-github-app)
và [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Cài App thử nghiệm lên một private repository dùng riêng cho việc kiểm thử, có
một lượng source code nhỏ. Trước khi thêm repository hoặc branch, xác nhận
workspace hiển thị trạng thái đã kết nối App.

## 5. Trình tự kiểm thử khói đầu tiên

1. Đăng ký/đăng nhập trên frontend staging local và tạo workspace. Nếu bật xác
   minh email, lấy mã xác minh từ MailHog tại `http://localhost:18025`.
2. Kết nối GitHub App staging và cấp quyền cho App truy cập private repository
   thử nghiệm.
3. Xem danh sách branch, thêm branch mặc định và chạy index lần đầu.
4. Theo dõi log của `backend` và `celery-worker`. Xác nhận job đầu tiên hoàn
   tất và `indexed_commit_sha` khớp commit đã fetch.
5. Push một thay đổi source. Trong cấu hình GitHub App, xác nhận webhook
   delivery thành công; xác nhận staging tạo một job và hoàn tất với indexed
   SHA mới.
6. Gửi lại cùng GitHub delivery. Xác nhận không tạo thêm indexing job.

Hiện chưa nên dùng chung một branch cho nhiều workspace trong smoke test này:
checkpoint và trạng thái đang ở cấp branch; cần chuyển chúng sang phạm vi
workspace trước khi hỗ trợ tình huống đó. Việc cleanup branch bị xóa và xóa dữ
liệu đã index khi quyền bị thu hồi cũng chưa được triển khai.

## Dọn staging sau khi kiểm thử

Dừng riêng Compose project staging bằng lệnh:

```powershell
docker compose --project-name source-context-staging -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.staging.yml --env-file .env.staging down
```

Giữ `.env.staging` và các volume nếu cần xem lại kết quả. Nếu muốn xóa dữ liệu
staging, trước hết xác nhận Compose project có tên
`source-context-staging`, sau đó chỉ xóa volume thuộc project đó.
