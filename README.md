# Telusko Trac - Product Inventory Management

A comprehensive product inventory management system built with FastAPI backend and React frontend, providing seamless tracking and management of product inventory.

## Features

- **GET /**: Welcome endpoint
- **GET /products/**: Get all products
- **GET /products/{product_id}**: Get a specific product by ID
- **POST /products/**: Create a new product

## Setup

1. **Copy .env file:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` và thay đổi các giá trị:
   - `DB_PASSWORD`: Mật khẩu SQL Server
   - `SECRET_KEY`: Tạo key mới với command:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Users

- **POST /users/** - Đăng ký user mới
- **POST /users/login** - Đăng nhập
- **GET /users/** - Lấy danh sách users
- **GET /users/{user_id}** - Lấy user theo ID
- **PUT /users/{user_id}** - Cập nhật user
- **DELETE /users/{user_id}** - Xóa user

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Project Structure

```
stocksphere/
├── main.py          # FastAPI application with endpoints
├── models.py        # Pydantic models
├── .gitignore       # Git ignore file
└── README.md        # This file
```

## API Usage Examples

### Get all products

```bash
curl http://localhost:8000/products/
```

### Get product by ID

```bash
curl http://localhost:8000/products/1
```

### Create a new product

```bash
curl -X POST "http://localhost:8000/products/" \
     -H "Content-Type: application/json" \
     -d '{
       "id": 5,
       "name": "Monitor",
       "description": "4K monitor",
       "price": 299.99,
       "quantity": 15
     }'
```

## Models

### Product

- `id`: integer
- `name`: string
- `description`: string
- `price`: float
- `quantity`: integer

## Built With

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation using Python type hints
- [Uvicorn](https://www.uvicorn.org/) - ASGI server implementation
