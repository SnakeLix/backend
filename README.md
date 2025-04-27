# FastAPI Backend

**Tác giả: Đỗng Gia Sang, Trần Công Toàn**

Một ứng dụng backend FastAPI với xác thực JWT, cơ sở dữ liệu PostgreSQL và cấu hình Docker.

## Tính năng

- Xác thực người dùng bằng JWT
- Đầy đủ CRUD cho người dùng và tài liệu
- Cơ sở dữ liệu PostgreSQL với SQLAlchemy ORM
- Alembic migrations
- Docker và docker-compose để triển khai dễ dàng
- Băm mật khẩu để bảo mật

## Cài đặt nhanh

1. Cài đặt các gói cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

2. Khởi động server phát triển:
   ```bash
   python dev_server.py
   ```

3. Có thể sử dụng ngrok để truy cập an toàn vào `/web`

## Lược đồ cơ sở dữ liệu

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

## Các endpoint API

- **Xác thực**
  - `POST /api/v1/auth/login` - Nhận JWT token

- **Người dùng**
  - `POST /api/v1/users` - Tạo người dùng mới
  - `GET /api/v1/users/me` - Lấy thông tin người dùng hiện tại
  - `PUT /api/v1/users/me` - Cập nhật người dùng hiện tại
  - `GET /api/v1/users` - Liệt kê tất cả người dùng (cần xác thực)

- **Tài liệu**
  - `GET /api/v1/documents` - Liệt kê tài liệu của người dùng
  - `POST /api/v1/documents` - Tạo tài liệu mới
  - `GET /api/v1/documents/{document_id}` - Lấy tài liệu cụ thể
  - `PUT /api/v1/documents/{document_id}` - Cập nhật tài liệu
  - `DELETE /api/v1/documents/{document_id}` - Xóa tài liệu

## Phát triển

1. Tạo môi trường ảo:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Windows: venv\Scripts\activate
   ```

2. Cài đặt phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

3. Thiết lập biến môi trường (sửa DATABASE_URL cho PostgreSQL cục bộ)

4. Chạy ứng dụng:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Chạy migrate database:
   ```bash
   alembic upgrade head
   ```

## Tạo migration mới

Sau khi thay đổi models, tạo migration mới:
```bash
alembic revision --autogenerate -m "Mô tả thay đổi"
alembic upgrade head
```
