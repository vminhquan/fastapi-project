# QTIK Cenimax Backend

Backend API cho hệ thống đặt vé xem phim QTIK Cenimax, được xây dựng bằng FastAPI, SQLAlchemy và PostgreSQL. Dự án cung cấp các nghiệp vụ cốt lõi cho ứng dụng web: xác thực người dùng, quản lý phim, phòng chiếu, suất chiếu, đặt vé, đơn hàng, thanh toán payOS, email OTP và chatbot AI.

## Tính năng chính

- Xác thực người dùng bằng JWT access token, refresh token và token blacklist.
- Đăng ký, đăng nhập, xác thực OTP, quên mật khẩu và đặt lại mật khẩu.
- Phân quyền `admin` cho các API quản trị phim, phòng, suất chiếu, booking và người dùng.
- Quản lý phim, phòng chiếu, ghế, suất chiếu và lịch chiếu.
- Đặt vé theo suất chiếu, giữ ghế tạm thời và tự động giải phóng booking quá hạn.
- Quản lý đơn hàng, vé điện tử, QR token và trạng thái sử dụng vé.
- Tạo link thanh toán, nhận webhook và đối soát thanh toán qua payOS.
- Gửi email qua Resend.
- Chatbot AI tích hợp qua Gemini/OpenAI-compatible API.

## Công nghệ sử dụng

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic Settings
- PostgreSQL qua `psycopg`
- python-jose, passlib, bcrypt
- Resend Email API
- payOS Payment API

## Cấu trúc thư mục

```text
app/
├── api/endpoints/       # Router theo từng nhóm nghiệp vụ
├── core/                # Cấu hình, database, security, dependency
├── models/              # SQLAlchemy models
├── repositories/        # Truy vấn dữ liệu theo domain
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic
└── main.py              # FastAPI app, middleware, router registration
```

## Yêu cầu hệ thống

- Python 3.11 hoặc mới hơn
- PostgreSQL database
- Tài khoản payOS nếu dùng thanh toán thật
- API key Resend nếu dùng gửi email
- API key Gemini/OpenAI nếu dùng chatbot

## Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Trên Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Cấu hình môi trường

Tạo file `.env` tại thư mục gốc backend:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
DIRECT_DATABASE_URL=

SECRET_KEY=change_me_to_a_long_random_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

ADMIN_EMAILS=admin@example.com

APP_TIMEZONE=Asia/Ho_Chi_Minh
BOOKING_HOLD_MINUTES=5
BOOKING_CLEANUP_INTERVAL_SECONDS=15

PAYOS_CLIENT_ID=
PAYOS_API_KEY=
PAYOS_CHECKSUM_KEY=
PAYOS_BASE_URL=
PAYOS_RETURN_URL=http://localhost:5173/payment/success
PAYOS_CANCEL_URL=http://localhost:5173/payment/cancel
PAYOS_REQUEST_TIMEOUT=15

RESEND_API_KEY=
RESEND_FROM_EMAIL=

GEMINI_API_KEY=
CHATGPT_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

Lưu ý:

- `DATABASE_URL` là biến bắt buộc.
- `SECRET_KEY` nên là chuỗi dài, ngẫu nhiên và không commit lên Git.
- `ADMIN_EMAILS` hỗ trợ nhiều email, phân tách bằng dấu phẩy. Khi server khởi động, các tài khoản có email này sẽ được nâng quyền `admin` nếu đã tồn tại.
- Các biến payOS, Resend và AI có thể để trống khi chưa dùng tính năng tương ứng.

## Chạy ứng dụng local

```bash
uvicorn app.main:app --reload
```

Mặc định server chạy tại:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Khi khởi động, ứng dụng sẽ:

- Tạo bảng database nếu chưa tồn tại thông qua `Base.metadata.create_all`.
- Seed quyền admin dựa trên `ADMIN_EMAILS`.
- Bật background task dọn booking/vé hết hạn theo `BOOKING_CLEANUP_INTERVAL_SECONDS`.

## Nhóm API chính

| Nhóm | Prefix | Mô tả |
| --- | --- | --- |
| Users | `/api/users` | Đăng ký, đăng nhập, OTP, profile, refresh token, quản trị user |
| Rooms | `/api/rooms` | Quản lý phòng chiếu |
| Events | `/api/events` | Quản lý suất chiếu, lịch chiếu và trạng thái ghế |
| Films | `/api/films` | Quản lý phim, danh sách phim, phim hot |
| Bookings | `/api/bookings` | Đặt vé, vé của tôi, QR ticket, cleanup booking |
| Orders | `/api/orders` | Đơn hàng của người dùng và quản trị đơn hàng |
| Payments | `/api/payments` | Link thanh toán, webhook payOS, đối soát thanh toán |
| Chatbot | `/api/chat` | Trợ lý AI |

## CORS

Backend hiện cho phép frontend local và production gọi API:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `https://qtik-frontend.onrender.com`
- `https://qtik.io.vn`
- `https://www.qtik.io.vn`

Nếu đổi domain frontend, cập nhật cấu hình CORS trong `app/main.py`.

## Kiểm tra nhanh

```bash
curl http://localhost:8000/
```

Kết quả mong đợi:

```json
{
  "status": "Hoạt động bình thường",
  "message": "Chào mừng đến với hệ thống API của tôi!"
}
```

## Quy trình phát triển đề xuất

1. Tạo branch riêng cho từng tính năng hoặc bản sửa lỗi.
2. Cập nhật schema/model/service tương ứng với domain đang thay đổi.
3. Kiểm tra thủ công trên Swagger UI sau khi thêm hoặc sửa API.
4. Không commit `.env`, token, API key, database password hoặc thông tin thanh toán thật.
5. Đồng bộ endpoint với frontend trong `src/constants/apiEndpoints.js` khi thay đổi prefix hoặc response contract.

## Liên kết với frontend

Frontend QTIK Cenimax gọi API qua base URL đang được khai báo trong:

```text
src/constants/apiEndpoints.js
```

Khi chạy local, nên dùng backend tại `http://localhost:8000/api` và frontend tại `http://localhost:5173`.
