# Edge Log Analytics Engine (DuckDB vs SQLite In-Situ)

Hệ thống phân tích logs IoT thời gian thực tại thiết bị biên sử dụng CSDL nhúng dạng cột **DuckDB (Vectorized Execution Engine)** và đối chuẩn so sánh với **SQLite (Row-oriented B-Tree)**.

---

## 📁 CẤU TRÚC PHÂN TÁCH MÁY CLIENT VÀ MÁY SERVER

Dự án được phân tách thành 2 thư mục độc lập sẵn sàng để triển khai trên 2 máy ảo (VM) Oracle Cloud:

```
edge-log-analytics/
├── client/                     # DÀNH CHO VM 1 (Mô phỏng cụm Edge Gateways / IoT Nodes)
│   ├── core/                   # DuckDB, SQLite, Ring Buffer, Sliding Window, Prometheus Exporter
│   ├── benchmark/              # Bộ sinh dữ liệu giả lập & kịch bản đối chuẩn tự động
│   ├── server/                 # FastAPI Web Server + WebSocket + /metrics Endpoint
│   ├── ui/                     # Dashboard giao diện tối (Dark Mode) thời gian thực tại chỗ
│   ├── Dockerfile              # Container image cho Edge Node
│   ├── docker-compose.yml       # Khởi chạy đồng thời 5 Edge Nodes (giới hạn 512MB RAM/node)
│   └── run.py                  # Entrypoint chạy trực tiếp bằng Python
│
└── cloud_server/               # DÀNH CHO VM 2 (Máy chủ Đám mây / Giám sát tập trung)
    ├── docker-compose.yml       # Khởi chạy Prometheus + Grafana + Cloud Parquet Receiver
    ├── prometheus.yml           # Cấu hình cào số liệu từ các Edge Nodes ở VM 1
    ├── receiver/               # API FastAPI nhận và lưu file Parquet tóm tắt nén từ Client
    └── grafana/
        └── edge_fleet_dashboard.json # File cấu hình Dashboard Grafana chuẩn hóa (Import 1-Click)
```

---

## 🚀 HƯỚNG DẪN TRIỂN KHAI

### 1. Triển khai trên VM 1 (Client / Edge Simulator):
```bash
cd client
docker compose up -d --build
```
*Hệ thống sẽ bật 5 Edge Gateway độc lập trên các cổng `8001, 8002, 8003, 8004, 8005`.*

### 2. Triển khai trên VM 2 (Cloud / Grafana Server):
```bash
cd cloud_server
# Chỉnh sửa IP của VM 1 trong prometheus.yml
docker compose up -d --build
```
- Mở Grafana tại: `http://<IP_VM_2>:3000` (User: `admin` / Pass: `admin`).
- Import file `cloud_server/grafana/edge_fleet_dashboard.json` để có ngay Dashboard hoàn chỉnh!
