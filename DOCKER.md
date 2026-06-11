# Hướng dẫn chạy bằng Docker - Student Weather Assistant

Tài liệu này hướng dẫn cách build và chạy toàn bộ dự án (Frontend, Backend và PostgreSQL Database) bằng Docker & Docker Compose.

---

## 1. Yêu cầu hệ thống
* **Docker Desktop** (hoặc Docker Engine).
* **Docker Compose**.
* **OpenWeather API Key** (Dự án sử dụng OpenWeather chính, tự động fallback sang Open-Meteo).

---

## 2. Thiết lập môi trường (`.env`)
Trước khi chạy Docker, bạn hãy tạo file `.env` bằng cách copy từ `.env.example`:

```bash
cp .env.example .env
```

Sau đó, cấu hình các biến môi trường thiết yếu trong `.env`:
```env
# Weather Provider Configuration
OPENWEATHER_API_KEY=your_openweather_api_key_here

# Database Configuration
POSTGRES_DB=student_weather
POSTGRES_USER=student_weather_user
POSTGRES_PASSWORD=secure_password_for_student_weather
DATABASE_URL=postgresql+asyncpg://student_weather_user:secure_password_for_student_weather@localhost:15432/student_weather

# JWT Config (Bảo mật tài khoản)
JWT_SECRET_KEY=change_me_to_a_secure_random_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google Login Config (Optional)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:18080/api/v1/auth/google/callback

# Email Notification Provider Configuration (Optional)
# A. SMTP Config
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
# B. Resend Config
RESEND_API_KEY=
EMAIL_FROM=
# C. SendGrid Config
SENDGRID_API_KEY=
```

---

## 3. Khởi động và Build Docker
Chạy lệnh duy nhất để build các service và khởi động container:

```bash
docker compose up --build
```

Docker Compose sẽ chạy:
1. **postgres** (Database): Cổng nội bộ `5432`, map ra cổng máy chủ **`15432`**.
2. **backend** (FastAPI): Cổng nội bộ `8000`, map ra cổng máy chủ **`18080`**.
3. **frontend** (React + Vite): Cổng nội bộ `80`, map ra cổng máy chủ **`15173`**.

---

## 4. Truy cập và Kiểm tra
* **Giao diện người dùng (Frontend):** [http://localhost:15173](http://localhost:15173)
* **Tài liệu API (Swagger UI):** [http://localhost:18080/docs](http://localhost:18080/docs)
* **API Health Check:** [http://localhost:18080/api/v1/health](http://localhost:18080/api/v1/health)
* **Cơ sở dữ liệu Postgres Host:** `localhost:15432`

---

## 5. Migration dữ liệu tự động
Khi container `backend` khởi động, script sẽ tự động kiểm tra và chạy:
```bash
alembic upgrade head
```
Điều này đảm bảo các bảng `users`, `user_locations`, `study_schedules`, và `user_settings` được tạo tự động mà không cần can thiệp thủ công.

---

## 6. Các lệnh quản trị hữu ích

* **Dừng các container:**
  ```bash
  docker compose down
  ```

* **Xóa hoàn toàn cơ sở dữ liệu và dữ liệu lưu (Reset DB):**
  ```bash
  docker compose down -v
  ```

* **Xem log của các container:**
  ```bash
  # Log của database
  docker compose logs -f postgres
  
  # Log của backend
  docker compose logs -f backend

  # Log của frontend
  docker compose logs -f frontend
  ```
