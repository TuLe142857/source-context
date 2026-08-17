Dưới đây là kết quả tra cứu chi tiết vị trí định nghĩa và danh sách các module / API router import và sử dụng `get_db`, `Settings` và `get_current_user` trong dự án FastAPI (thông qua công cụ **Source Context MCP** trên cây cú pháp AST: `workspace_id=1`, `repository_id=1`, `branch='master'`):

---

### 1. Nơi định nghĩa (Definitions)

| Tên Class / Phương thức | File định nghĩa | Cú pháp định nghĩa | Mô tả |
| :--- | :--- | :--- | :--- |
| **`get_db`** | [app/api/deps.py](file:///workspace-repositories/repo_1/master/backend/app/api/deps.py#L20-L22) | `def get_db() -> Generator[Session]:` | Generator dependency khởi tạo và quản lý lifecycle của SQLModel `Session`. Dùng để tạo type alias `SessionDep = Annotated[Session, Depends(get_db)]`. |
| **`Settings`** | [app/core/config.py](file:///workspace-repositories/repo_1/master/backend/app/core/config.py#L24-L114) | `class Settings(BaseSettings):` | Class kế thừa `BaseSettings` (Pydantic Settings) đọc các biến môi trường từ file `.env` và thiết lập cấu hình ứng dụng. Khởi tạo sẵn thành instance `settings = Settings()`. |
| **`get_current_user`** | [app/api/deps.py](file:///workspace-repositories/repo_1/master/backend/app/api/deps.py#L29-L45) | `def get_current_user(session: SessionDep, token: TokenDep) -> User:` | Dependency giải mã JWT Token, xác thực thông tin và kiểm tra trạng thái hoạt động của người dùng hiện t���i. Dùng để tạo `CurrentUser = Annotated[User, Depends(get_current_user)]`. |

---

### 2. Danh sách các Module & API Router sử dụng

#### A. Đối với `get_db`
* **Khai báo & import trực tiếp:**
  * [app/api/deps.py](file:///workspace-repositories/repo_1/master/backend/app/api/deps.py): Khai báo hàm `get_db` và gắn dependency vào `SessionDep = Annotated[Session, Depends(get_db)]`.
* **Sử dụng gián tiếp qua `SessionDep` tại các API Router:**
  * [app/api/routes/login.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/login.py): Router xử lý đăng nhập, khôi phục và đặt lại mật khẩu.
  * [app/api/routes/users.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/users.py): Router CRUD thông tin người dùng.
  * [app/api/routes/items.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/items.py): Router CRUD danh sách items.
  * [app/api/routes/private.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/private.py): Router tạo tài khoản nội bộ (internal).

#### B. Đối với `Settings` (hoặc instance `settings`)
* **Core & App Modules:**
  * [app/core/config.py](file:///workspace-repositories/repo_1/master/backend/app/core/config.py): Nơi định nghĩa class `Settings` và đối tượng `settings`.
  * [app/core/db.py](file:///workspace-repositories/repo_1/master/backend/app/core/db.py): Import `settings` để tạo kết nối database (`SQLALCHEMY_DATABASE_URI`) và thông tin tài khoản superuser đầu tiên.
  * [app/api/deps.py](file:///workspace-repositories/repo_1/master/backend/app/api/deps.py): Import `settings` cấu hình OAuth2 URL (`API_V1_STR`) và `SECRET_KEY`.
  * [app/main.py](file:///workspace-repositories/repo_1/master/backend/app/main.py): Import `settings` cấu hình FastAPI app (`title`, `openapi_url`, CORS origins, Sentry DSN).
  * [app/utils.py](file:///workspace-repositories/repo_1/master/backend/app/utils.py): Import `settings` cấu hình gửi email (SMTP), thời hạn token và secret key.
  * [app/alembic/env.py](file:///workspace-repositories/repo_1/master/backend/app/alembic/env.py): Import `settings` cấu hình chuỗi kết nối database khi chạy migration script.
* **API Routers:**
  * [app/api/routes/login.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/login.py): Import `settings` lấy `ACCESS_TOKEN_EXPIRE_MINUTES`.
  * [app/api/routes/users.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/users.py): Import `settings` kiểm tra trạng thái gửi email (`emails_enabled`).
* **Test Modules:**
  * [tests/conftest.py](file:///workspace-repositories/repo_1/master/backend/tests/conftest.py)
  * [tests/utils/utils.py](file:///workspace-repositories/repo_1/master/backend/tests/utils/utils.py)
  * [tests/utils/user.py](file:///workspace-repositories/repo_1/master/backend/tests/utils/user.py)
  * [tests/api/routes/test_login.py](file:///workspace-repositories/repo_1/master/backend/tests/api/routes/test_login.py)
  * [tests/api/routes/test_items.py](file:///workspace-repositories/repo_1/master/backend/tests/api/routes/test_items.py)
  * [tests/api/routes/test_users.py](file:///workspace-repositories/repo_1/master/backend/tests/api/routes/test_users.py)
  * [tests/api/routes/test_private.py](file:///workspace-repositories/repo_1/master/backend/tests/api/routes/test_private.py)

#### C. Đối với `get_current_user`
* **Khai báo & import trực tiếp:**
  * [app/api/deps.py](file:///workspace-repositories/repo_1/master/backend/app/api/deps.py): Khai báo `get_current_user` và liên kết vào `CurrentUser = Annotated[User, Depends(get_current_user)]`.
* **Sử dụng gián tiếp qua `CurrentUser` tại các API Router:**
  * [app/api/routes/users.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/users.py): Sử dụng trong các endpoint `/me`, `/me/password`, `/{user_id}` để lấy thông tin hoặc phân quyền.
  * [app/api/routes/items.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/items.py): Sử dụng trong toàn bộ các endpoint CRUD items để gắn `owner_id` hoặc xác minh quyền sở hữu/superuser.
  * [app/api/routes/login.py](file:///workspace-repositories/repo_1/master/backend/app/api/routes/login.py): Sử dụng trong endpoint `/login/test-token`.
