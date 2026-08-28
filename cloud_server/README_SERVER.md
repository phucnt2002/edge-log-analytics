# Hướng Dẫn Deploy Máy Chủ Trung Tâm (VM 2 - Cloud Server)

Thư mục này chứa toàn bộ cấu hình để triển khai **Grafana + Prometheus + Cloud Receiver** trên VM 2 (Oracle Cloud).

---

## 1. Các bước triển khai trên VM 2

### Bước 1: Copy thư mục `cloud_server` lên VM 2
```bash
scp -r ./cloud_server ubuntu@<IP_VM_2>:~/cloud_server
```

### Bước 2: Chỉnh sửa file `prometheus.yml`
Điền địa chỉ IP Public của **VM 1** vào file `prometheus.yml`:
```yaml
      - targets:
          - '<IP_VM_1>:8001'
          - '<IP_VM_1>:8002'
          - '<IP_VM_1>:8003'
          - '<IP_VM_1>:8004'
          - '<IP_VM_1>:8005'
```

### Bước 3: Khởi chạy toàn bộ hệ thống
```bash
cd ~/cloud_server
docker compose up -d --build
```

---

## 2. Truy cập Grafana
- URL: **`http://<IP_VM_2>:3000`**
- Tài khoản mặc định: `admin` / `admin`
- Thêm Data Source: **Prometheus** (`http://prometheus:9090`)
- Import file Dashboard dựng sẵn từ: `cloud_server/grafana/edge_fleet_dashboard.json`
