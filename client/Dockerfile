# Dockerfile for Edge Log Analytics (DuckDB vs SQLite)
FROM python:3.12-slim

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Tạo thư mục data nếu chưa có
RUN mkdir -p data/parquet_rollups data/benchmark

# Mở cổng giao diện Dashboard nội bộ
EXPOSE 8000

# Khởi chạy hệ thống mặc định
CMD ["python", "run.py"]
