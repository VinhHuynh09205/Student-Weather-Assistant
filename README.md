# Student Weather Assistant

Backend FastAPI & Frontend React cho website dự báo thời tiết hỗ trợ học sinh/sinh viên đi học hằng ngày, tự động đồng bộ hóa lịch học, vị trí đã lưu và cài đặt cá nhân với cơ sở dữ liệu PostgreSQL.

## Công nghệ

- Backend: FastAPI, SQLAlchemy 2.x, Alembic migrations, bcrypt, PyJWT, Uvicorn
- Frontend: React + Vite + TypeScript, Context API
- Database: PostgreSQL (asyncpg driver)
- Containerization: Docker & Docker Compose
- Weather Providers: OpenWeather (chính) & Open-Meteo (fallback)

## Vì sao chọn Open-Meteo

Open-Meteo miễn phí, không cần API key, có cả Geocoding API và Forecast API. Điều này phù hợp với đồ án sinh viên và giúp backend chạy được ngay sau khi cài dependency.

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Chạy backend

```bash
uvicorn app.main:app --reload
```

Sau khi chạy, truy cập:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

## Chạy test

```bash
pytest
```

Các unit test dùng service giả/mock dependency, không gọi API Open-Meteo thật.

## Endpoint

### GET `/api/v1/health`

Response:

```json
{
  "status": "ok",
  "service": "student-weather-assistant"
}
```

### GET `/api/v1/weather/current?city=Can Tho`

Lấy thời tiết hiện tại theo thành phố.

```json
{
  "city": "Can Tho",
  "country": "Vietnam",
  "latitude": 10.0333,
  "longitude": 105.7833,
  "timezone": "Asia/Ho_Chi_Minh",
  "current": {
    "temperature_c": 31.2,
    "apparent_temperature_c": 35.0,
    "relative_humidity_percent": 72,
    "precipitation_mm": 0.0,
    "rain_mm": 0.0,
    "weather_code": 3,
    "weather_description": "Nhiều mây",
    "wind_speed_kmh": 12.5,
    "uv_index": 6.2,
    "time": "2026-06-05T10:00"
  }
}
```

### GET `/api/v1/weather/hourly?city=Can Tho&hours=24`

`hours` chỉ nhận `6`, `12`, `24`, hoặc `48`.

### POST `/api/v1/weather/student-advice`

Request:

```json
{
  "city": "Can Tho",
  "study_shift": "afternoon",
  "vehicle_type": "motorbike"
}
```

`study_shift`: `morning`, `afternoon`, `evening`.

`vehicle_type`: `motorbike`, `bus`, `walking`, `bicycle`.

Response trả về điểm thuận lợi từ 0 đến 100, phân loại mức độ, chỉ số thời tiết trong ca học, lời khuyên, cảnh báo và forecast theo giờ đã lọc.

Mỗi item trong `hourly_forecast` có đủ dữ liệu cho frontend đổi nền động: `time`, `temperature_c`, `precipitation_probability_percent`, `weather_code`, `weather_description`, `wind_speed_kmh`, và `is_day`.

## Cấu trúc

```text
app/
  api/v1/endpoints/
  clients/
  core/
  models/
  schemas/
  services/
  utils/
tests/
```

Route chỉ nhận request và trả response. Business logic nằm trong service. Client chỉ gọi Open-Meteo. Schema Pydantic chịu trách nhiệm validation request/response.

---

## Xác thực & Phân quyền (Authentication & Authorization)

Hệ thống hỗ trợ 2 hình thức xác thực chính:
1. **Local Account (Tài khoản hệ thống)**:
   - Sử dụng **Username** và **Password** để đăng nhập/đăng ký. Không sử dụng email cho tài khoản local.
   - Khi đăng ký, sinh viên nhập: Họ và tên (`full_name`), Tên đăng nhập (`username`), Mật khẩu (`password`), và Xác nhận mật khẩu (`confirm_password`).
   - Tên đăng nhập phải dài tối thiểu 3 ký tự, tối đa 30 ký tự, và chỉ bao gồm chữ cái, số, dấu gạch dưới `_`, và dấu chấm `.`.

2. **OAuth Providers (Google Login)**:
   - Email chỉ bắt buộc đối với các tài khoản đăng nhập qua Google.
   - Tài khoản OAuth sẽ tự động sinh tên đăng nhập ngẫu nhiên từ email/name, và chào sinh viên bằng tên thực tế từ tài khoản mạng xã hội.
   - Nếu chưa cấu hình OAuth, hệ thống vẫn hoạt động bình thường với tài khoản local.

### Cấu hình Google Login
1. Truy cập **Google Cloud Console**, tạo một dự án mới và tạo **OAuth client ID** dạng Web Application.
2. Thiết lập Authorized JavaScript Origins là `http://localhost:5173` (hoặc domain frontend của bạn).
3. Thiết lập Authorized redirect URIs là `http://localhost:18080/api/v1/auth/google/callback` (hoặc callback URL của backend).
4. Điền các giá trị vào file `.env`:
   - `GOOGLE_CLIENT_ID` (backend) và `VITE_GOOGLE_CLIENT_ID` (frontend)
   - `GOOGLE_CLIENT_SECRET` (backend, nếu dùng callback)
   - `GOOGLE_REDIRECT_URI` (backend)

---

## Hệ thống Thông báo (Notification System)

Ứng dụng hỗ trợ 3 kênh thông báo (Notification Channels) khác nhau để gửi cảnh báo thời tiết trước giờ học:

1. **In-app Notification**: Hiển thị thông báo toast trực tiếp trên màn hình khi người dùng đang mở ứng dụng.
2. **Browser Notification**: Sử dụng Browser Notification API để đẩy thông báo trên màn hình máy tính/thiết bị của sinh viên khi trang web đang mở. Kênh này yêu cầu người dùng cấp quyền (Permission).
3. **Email Notification**: Gửi email thực tế về địa chỉ email của sinh viên (đối với tài khoản Google hoặc tài khoản local có cập nhật email).

### Cấu hình Email Provider

Để sử dụng tính năng thông báo qua Email, bạn cần cấu hình tối thiểu một trong các nhà cung cấp (provider) sau trong file `.env`:

#### A. Cấu hình qua SMTP:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
```

#### B. Cấu hình qua Resend API:
```env
RESEND_API_KEY=re_your_resend_api_key
EMAIL_FROM=onboarding@resend.dev
```

#### C. Cấu hình qua SendGrid API:
```env
SENDGRID_API_KEY=sg_your_sendgrid_api_key
EMAIL_FROM=your-verified-sender@sendgrid.com
```

*Lưu ý:* Nếu không cấu hình email provider, hệ thống sẽ tự động chỉ dùng in-app và browser notification để gửi thông báo thử nghiệm và reminder lịch học. Trạng thái gửi thông báo qua email sẽ ghi nhận là `failed` với lý do thiếu cấu hình thay vì giả lập gửi thành công.

### Khuyến nghị cho Production

1. **Worker Lịch trình (Scheduled Worker)**: Trong môi trường production, khuyến nghị tách tác vụ quét lịch học và gửi thông báo ra khỏi FastAPI server chính. Sử dụng một hệ thống hàng đợi tác vụ như **Celery**, **RQ**, hoặc thư viện lập lịch **APScheduler** kết hợp Redis/RabbitMQ.
2. **Offline Browser Push**: Để gửi browser notification khi tab web đã đóng, cần triển khai giao thức **Web Push** kết hợp với **Service Worker** và chứng chỉ khóa **VAPID**.
