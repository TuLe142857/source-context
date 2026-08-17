Dưới đây là thông tin chi tiết về nơi định nghĩa và các router/module sử dụng hàm `get_db` trong dự án FastAPI này:

---

### 1. Nơi định nghĩa `get_db`

* **File:** [main.py](file:///C:/Users/HUU%20HIEU/.gemini/antigravity-cli/scratch/fastapi_sqlalchemy_demo/main.py#L36-L43) (Dòng 36 – 43)
* **Mã nguồn định nghĩa:**
```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    print("\n[LAYER 5: SQLAlchemy Session] Open Session (SessionLocal())")
    try:
        yield db
    finally:
        print("[LAYER 5: SQLAlchemy Session] Close Session (db.close() context manager clean-up)")
        db.close()
```
* **Chức năng:** Đây là một **Dependency Provider** cho SQLAlchemy Session trong FastAPI. Nó tạo mới một phiên làm việc với database (`SessionLocal()`), cùng cú pháp `yield` để truyền session cho request handler, sau đó tự động đóng phiên (`db.close()`) trong khối `finally` sau khi hoàn tất HTTP request lifecycle.

---

### 2. Các API Router & Endpoint đang sử dụng `get_db`

Tất cả các API router và endpoint sau đều nằm trong module [main.py](file:///C:/Users/HUU%20HIEU/.gemini/antigravity-cli/scratch/fastapi_sqlalchemy_demo/main.py#L125-L156) thuộc APIRouter `router` (`prefix="/auth"`):

1. **Endpoint Đăng ký tài khoản (`POST /auth/register`)**
   * **Vị trí:** [main.py](file:///C:/Users/HUU%20HIEU/.gemini/antigravity-cli/scratch/fastapi_sqlalchemy_demo/main.py#L127-L128)
   * **Cú pháp sử dụng:**
     ```python
     @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
     def register(user_in: UserCreate, db: Session = Depends(get_db)):
     ```

2. **Endpoint Đăng nhập (`POST /auth/login`)**
   * **Vị trí:** [main.py](file:///C:/Users/HUU%20HIEU/.gemini/antigravity-cli/scratch/fastapi_sqlalchemy_demo/main.py#L141-L142)
   * **Cú pháp sử dụng:**
     ```python
     @router.post("/login", response_model=TokenResponse)
     def login(login_data: UserLogin, db: Session = Depends(get_db)):
     ```

---

### 💡 Ghi chú
* Dự án hiện tại tổ chức monolith đơn giản trong file [main.py](file:///C:/Users/HUU%20HIEU/.gemini/antigravity-cli/scratch/fastapi_sqlalchemy_demo/main.py). `get_db` được tham chiếu trực tiếp qua `Depends(get_db)` mà không cần `import` từ module bên ngoài.
* Không tìm thấy định nghĩa `Settings` hoặc `get_current_user` trong codebase này.
