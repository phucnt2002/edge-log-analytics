# 🚀 Edge Log Analytics Engine: DuckDB vs SQLite In-Situ

> **Học phần:** Cơ sở dữ liệu nâng cao (CSDLNC) — Chương trình Thạc sĩ CNTT, Đại học Công nghệ Thông tin (UIT - ĐHQG-HCM)  
> **Đề tài:** Nghiên cứu và hiện thực hóa hệ thống phân tích nhật ký (Logs) thời gian thực tại thiết bị biên (Edge Computing): Đối chuẩn hiệu năng chuyên sâu giữa **DuckDB (Vectorized Columnar OLAP)** và **SQLite (B-Tree Row-oriented OLTP)**.

---

## 📌 MỤC LỤC
1. [Giới Thiệu & Đặt Vấn Đề](#-giới-thiệu--đặt-vấn-đề)
2. [Kiến Trúc Tổng Thể Hệ Thống (Two-Tier Architecture)](#-kiến-trúc-tổng-thể-hệ-thống-two-tier-architecture)
3. [So Sánh Cốt Lõi: DuckDB vs SQLite Tại Biên](#-so-sánh-cốt-lõi-duckdb-vs-sqlite-tại-biên)
4. [Cấu Trúc Thư Mục Dự Án](#-cấu-trúc-thư-mục-dự-án)
5. [Hướng Dẫn Cài Đặt & Triển Khai](#-hướng-dẫn-cài-đặt--triển-khai)
6. [Bộ Đo Kiểm Đối Chuẩn (Benchmark Suite)](#-bộ-đo-kiểm-đối-chuẩn-benchmark-suite)
7. [Cơ Chế Tiết Kiệm Băng Thông Cloud (Rollup & Parquet Sync)](#-cơ-chế-tiết-kiệm-băng-thông-cloud-rollup--parquet-sync)
8. [Hệ Thống Giám Sát & Bảng Điều Khiển (Grafana & Local UI)](#-hệ-thống-giám-sát--bảng-điều-khiển-grafana--local-ui)
9. [Danh Mục API Endpoints](#-danh-mục-api-endpoints)

---

## 🎯 GIỚI THIỆU & ĐẶT VẤN ĐỀ

Trong kỷ nguyên IoT, các thiết bị tại biên (Edge Gateways, trạm thu phát, camera AI, router công nghiệp) sinh ra hàng trăm triệu dòng log mỗi ngày. Mô hình truyền thống **Cloud-Centric** (đẩy toàn bộ raw log JSON về máy chủ đám mây như Elasticsearch, BigQuery) gặp 3 rào cản nghiêm trọng:
1. **Nghẽn băng thông và chi phí mạng khổng lồ (Egress Cost):** Log thô dạng chuỗi JSON chiếm dung lượng lớn, tốn kém chi phí gói cước viễn thông 4G/5G/WAN.
2. **Độ trễ phát hiện sự cố cao:** Chờ log truyền về Cloud mới truy vấn khiến việc phát hiện tấn công DDoS, brute-force hay lỗi hệ thống bị trễ nhiều phút.
3. **Mất khả năng tự trị khi mất kết nối mạng (Network Partition):** Khi rớt mạng WAN, thiết bị biên hoàn toàn "mù" thông tin vận hành nội bộ.

**Giải pháp đề xuất: Phân tích tại chỗ (In-Situ Edge Analytics)**  
Tích hợp một Cơ sở dữ liệu nhúng (Embedded DBMS) trực tiếp vào thiết bị biên:
- Thu thập, lọc và phân tích bất thường trên cửa sổ trượt (Sliding Window 60s) ngay tại chỗ.
- Kích hoạt cảnh báo khẩn cấp tức thì (độ trễ dưới 50ms).
- Định kỳ gom nhóm dữ liệu (Rollup 15 phút), nén theo dạng cột (**Parquet ZSTD**) rồi mới đồng bộ về Cloud, giúp **tiết kiệm hơn 99% băng thông mạng**.

---

## 🏛 KIẾN TRÚC TỔNG THỂ HỆ THỐNG (TWO-TIER ARCHITECTURE)

Hệ thống được thiết kế theo mô hình 2 tầng phân tán: **Edge Fleet (Tầng biên)** và **Central Cloud Platform (Tầng trung tâm)**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TẦNG BIÊN (EDGE FLEET COMPUTING)                                │
│                                                                                        │
│   IoT Sensors / Web Traffic (Access Logs Stream)                                      │
│           │                                                                            │
│           ▼                                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ IngestBuffer (asyncio.Queue, Micro-batching 500 rows / 500ms)                  │   │
│   │       │ (Zero-copy in-memory)                                                  │   │
│   │       ▼                                                                        │   │
│   │ Apache Arrow Table (pa.Table)                                                  │   │
│   │       │                                                                        │   │
│   │       ▼                                                                        │   │
│   │ DuckDB Engine (Vectorized Storage: edge_logs_{NODE_ID}.duckdb)                 │   │
│   │   ├── StreamAnalyzer (Cửa sổ trượt 60s, chạy định kỳ mỗi 1s)                   │   │
│   │   │     ├── AlertManager (Đánh giá luật ngưỡng: Error Rate, P99, DDOS)         │   │
│   │   │     └── WebSocket Broadcast ──► Local Web Dashboard (Chart.js / Dark UI)   │   │
│   │   │                                                                            │   │
│   │   ├── CloudSyncer (Chạy ngầm mỗi 30s: Rollup 15-min ──► Parquet ZSTD)          │   │
│   │   └── Prometheus Exporter (/metrics: Memory, CPU, Latency P99, Alert count)    │   │
│   └───────┬─────────────────────────────────────────────────┬──────────────────────┘   │
└───────────┼─────────────────────────────────────────────────┼──────────────────────────┘
            │ (HTTP POST Parquet Rollup)                      │ (Scrape /metrics)
            ▼                                                 ▼
┌──────────────────────────────────────────┐    ┌────────────────────────────────────────┐
│ Cloud Parquet Receiver (FastAPI)         │    │ Cloud Prometheus Server                │
│ Endpoint: /api/upload-parquet            │    │ Scrape Interval: 5s                    │
│ Lưu trữ: cloud_server/cloud_data/*.parquet│    │ Target: edge-gateway-01, 02...         │
└──────────────────────────────────────────┘    └──────────────────┬─────────────────────┘
                                                                   │ (PromQL Queries)
                                                                   ▼
                                                ┌────────────────────────────────────────┐
                                                │ Grafana Central Fleet Dashboard        │
                                                │ Giám sát tập trung toàn bộ Gateways   │
                                                │ Port: 3000 (User: admin / Pass: admin) │
                                                └────────────────────────────────────────┘
                        TẦNG ĐÁM MÂY (CENTRAL CLOUD MONITORING)
```

---

## ⚖ SO SÁNH CỐT LÕI: DUCKDB VS SQLITE TẠI BIÊN

| Tiêu Chí Kỹ Thuật | SQLite (Row-oriented OLTP) | DuckDB (Vectorized Columnar OLAP) | Đánh Giá Ý Nghĩa Tại Biên |
| :--- | :--- | :--- | :--- |
| **Mô hình tổ chức dữ liệu** | **Dòng (Row-oriented B-Tree)**. Cả dòng lưu liền kề nhau trên data pages. | **Cột (Columnar Storage)**. Cùng kiểu dữ liệu theo cột, nén Dictionary/Bitpacking. | DuckDB tối ưu vượt trội cho các câu lệnh tính toán, quét và gom nhóm (GROUP BY). |
| **Mô hình thực thi truy vấn** | **Volcano Iterator (Tuple-at-a-time)**. Tốn chi phí gọi hàm ảo (function call overhead). | **Vectorized Execution Engine**. Xử lý khối vector (2048 giá trị/lần) trong Cache CPU, dùng tập lệnh SIMD. | DuckDB tận dụng triệt để năng lực CPU hạn chế của chip ARM/x86 thiết bị biên. |
| **Hàm phân vị (Percentiles)** | Không hỗ trợ native (phải nạp toàn bộ vào RAM rồi sắp xếp lại qua subquery). | Hỗ trợ native: `QUANTILE_CONT(latency_ms, 0.99)`. | DuckDB tính toán P95, P99 độ trễ trong mili-giây mà không làm tăng tải RAM. |
| **Tính năng xuất nén Parquet** | ❌ **Không có native**. Phải đọc từng dòng ra Python, dùng thư viện ngoài (`pyarrow`) để ép kiểu. Dễ bị tràn RAM (OOM). | ✅ **Native Zero-Copy**: Lệnh `COPY (...) TO 'f.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)` chạy thẳng bằng C++. | DuckDB nén và xuất file Parquet siêu nhẹ, sẵn sàng đẩy về Data Lake/Cloud. |
| **Khóa tệp & Đa tiến trình** | Tốt trong kịch bản nhiều kết nối đọc ghi đồng thời nhờ cơ chế **WAL (Write-Ahead Logging)**. | Khóa độc quyền khi ghi (`_duckdb.IOException: Conflicting lock`). Mỗi process/node cần DB file riêng. | Phù hợp mô hình: 1 Edge Node sở hữu 1 file DuckDB độc lập (`edge_logs_{NODE_ID}.duckdb`). |
| **Dung lượng lưu trữ đĩa** | Dung lượng lớn hơn do overhead của B-Tree và metadata từng dòng. | Tiết kiệm từ **60% - 80% dung lượng đĩa** nhờ thuật toán nén dạng cột. | Rất quan trọng cho các ổ cứng Flash/eMMC dung lượng nhỏ trên Gateway. |

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```
edge-log-analytics/
├── docker-compose.yml              # Khởi chạy toàn bộ hệ thống (2 Edge Nodes + Cloud Stack)
├── README.md                       # Tài liệu hướng dẫn chi tiết
│
├── client/                         # TẦNG BIÊN (Edge Gateway Node)
│   ├── Dockerfile                  # Container đóng gói Edge Node (Python 3.12-slim)
│   ├── docker-compose.yml          # Kịch bản chạy độc lập cụm 5 Edge Gateways
│   ├── requirements.txt            # Thư viện phụ thuộc (duckdb, pyarrow, fastapi, prometheus-client...)
│   ├── run.py                      # Entrypoint khởi động máy chủ biên
│   ├── download_dataset.py         # Script kiểm tra/tạo dữ liệu chuẩn Kaggle Web Access Logs Labeled
│   │
│   ├── core/                       # Lõi xử lý cơ sở dữ liệu và phân tích luồng
│   │   ├── duckdb_engine.py        # Động cơ DuckDB: schema, insert arrow, vectorized queries, parquet rollup
│   │   ├── sqlite_engine.py        # Động cơ SQLite: schema B-Tree, pragma WAL, baseline queries
│   │   ├── ingestion.py            # Hàng đợi IngestBuffer bất đồng bộ micro-batching
│   │   ├── analyzer.py             # StreamAnalyzer tính toán sliding window 60s
│   │   ├── alert_manager.py        # Đánh giá cảnh báo dựa trên rules.json
│   │   ├── cloud_syncer.py         # Cơ chế rollup nén Parquet và HTTP POST lên Cloud
│   │   └── metrics.py              # Bộ chỉ số Prometheus Exporter chuẩn OpenMetrics
│   │
│   ├── benchmark/                  # Bộ công cụ đo kiểm đối chuẩn tự động
│   │   ├── generator.py            # Sinh log giả lập chuẩn cấu trúc (HTTP method, IP, latency, attack label)
│   │   ├── runner.py               # Kịch bản benchmark 5 bài toán: Ingest, Filter, GroupBy, P99, Storage
│   │   └── visualizer.py           # Xuất biểu đồ so sánh tự động (PNG)
│   │
│   ├── server/                     # Máy chủ web tại biên
│   │   └── app.py                  # FastAPI server, WebSocket hub, background lifecycle tasks
│   │
│   ├── ui/                         # Giao diện giám sát tại chỗ (Local Dark Dashboard)
│   │   ├── templates/index.html    # Giao diện HTML Chart.js
│   │   └── static/                 # CSS/JS phụ trợ
│   │
│   └── data/                       # Thư mục lưu trữ database cục bộ (.duckdb, .sqlite, .parquet)
│
└── cloud_server/                   # TẦNG ĐÁM MÂY (Central Monitoring & Data Lake)
    ├── docker-compose.yml          # Khởi chạy riêng cụm Cloud (Prometheus, Grafana, Receiver)
    ├── prometheus.yml              # Cấu hình Scrape Target các Edge Gateways
    │
    ├── receiver/                   # Dịch vụ tiếp nhận file Parquet từ các trạm biên
    │   ├── app.py                  # FastAPI endpoint nhận multipart/form-data
    │   └── Dockerfile
    │
    ├── grafana/                    # Bảng điều khiển trung tâm
    │   ├── edge_fleet_dashboard.json # Toàn bộ cấu hình Panels Dashboard hoàn chỉnh
    │   └── provisioning/           # Tự động nạp Datasource và Dashboard khi khởi động
    │
    └── cloud_data/                 # Kho lưu trữ file Parquet tổng hợp nhận từ Edge
```

---

## ⚡ HƯỚNG DẪN CÀI ĐẶT & TRIỂN KHAI

### Cách 1: Chạy toàn bộ hệ thống bằng Docker Compose (Khuyến nghị cho Demo)
Chỉ cần 1 câu lệnh tại thư mục gốc để khởi chạy toàn bộ 5 dịch vụ:

```bash
docker compose up --build -d
```

Sau khi khởi động thành công, các dịch vụ sẽ sẵn sàng tại:
* **Grafana Central Dashboard:** [http://localhost:3000](http://localhost:3000) *(Tài khoản: `admin` / Mật khẩu: `admin`)*
* **Edge Gateway 01 (Local UI):** [http://localhost:8001](http://localhost:8001)
* **Edge Gateway 02 (Local UI):** [http://localhost:8002](http://localhost:8002)
* **Prometheus Server:** [http://localhost:9090](http://localhost:9090)
* **Cloud Parquet Receiver:** [http://localhost:5000](http://localhost:5000)

Dừng hệ thống:
```bash
docker compose down
```

---

### Cách 2: Triển khai phân tán trên 2 máy ảo độc lập (Oracle Cloud / AWS)

#### Máy ảo 1: Edge Fleet Simulator (Client)
```bash
cd client
docker compose up -d --build
```
*Sẽ kích hoạt 5 trạm biên trên các cổng `8001, 8002, 8003, 8004, 8005` (giới hạn cứng 512MB RAM/node).*

#### Máy ảo 2: Central Cloud Monitoring
1. Mở file `cloud_server/prometheus.yml`, trỏ địa chỉ IP mục tiêu về IP của Máy ảo 1:
   ```yaml
   targets: ['<IP_MAY_AO_1>:8001', '<IP_MAY_AO_1>:8002']
   ```
2. Khởi chạy máy chủ Cloud:
   ```bash
   cd cloud_server
   docker compose up -d --build
   ```
3. Truy cập Grafana tại `http://<IP_MAY_AO_2>:3000`.

---

### Cách 3: Chạy trực tiếp bằng Python (Môi trường phát triển cục bộ)
Yêu cầu: **Python 3.10+**

```bash
cd client
pip install -r requirements.txt

# Khởi chạy node biên
python run.py
```
Truy cập giao diện tại: [http://localhost:8000](http://localhost:8000).

---

## 📊 BỘ ĐO KIỂM ĐỐI CHUẨN (BENCHMARK SUITE)

Hệ thống tích hợp sẵn kịch bản Benchmark đo lường tự động trên 5 bài toán kinh điển:

```bash
# Chạy đối chuẩn mặc định 100,000 bản ghi
python client/benchmark/runner.py 100000

# Hoặc đo kiểm với tải lớn: 500,000 bản ghi
python client/benchmark/runner.py 500000
```

Sau khi chạy xong, kết quả lưu vào `client/data/benchmark_results.json` và xuất ảnh biểu đồ tự động tại `client/data/benchmark_results.png`.

### 6 Kịch bản kiểm thử chuẩn hóa (Kế thừa từ ClickBench & TSBS):
1. **Batch Ingestion Rate (Tốc độ nạp dữ liệu):**  
   Đo tốc độ chèn qua micro-batching (Apache Arrow nạp vào DuckDB vs Prepared Statements nạp vào SQLite WAL).
2. **Q1 - Attack Detection & Count (Lọc & Đếm log tấn công):**  
   `SELECT COUNT(*) FROM edge_logs WHERE label = 'attack';`
3. **Q2 - Multi-dimensional Aggregation (Gom nhóm theo IP & Loại tấn công):**  
   `SELECT client_ip, attack_type, COUNT(*), AVG(bytes_sent) FROM edge_logs WHERE label = 'attack' GROUP BY client_ip, attack_type;`
4. **Q3 - Heavy Multi-Agg (Tổng hợp tải lỗi Server 5xx):**  
   `SELECT COUNT(*), AVG(bytes_sent), MAX(bytes_sent), MIN(bytes_sent) FROM edge_logs WHERE status_code >= 500;`
5. **Q4 - Percentile / Quantile Calculation (Độ trễ P99 Latency Math):**  
   Đo kiểm khả năng tính phân vị thời gian thực:
   - DuckDB: Sử dụng `QUANTILE_CONT(bytes_sent, 0.99)` Vectorized.
   - SQLite: Sắp xếp bằng B-Tree offset subquery.
6. **Q5 - Text Pattern Search (Quét mẫu chuỗi URL tiêm SQL/Admin):**  
   `SELECT COUNT(*) FROM edge_logs WHERE endpoint LIKE '%union%' OR endpoint LIKE '%select%' OR endpoint LIKE '%admin%';`
7. **Q6 - Global Fleet Aggregation (Gom nhóm tổng hợp toàn diện 100% logs):**  
   `SELECT method, COUNT(*), ROUND(AVG(latency_ms), 2), SUM(bytes_sent) FROM edge_logs GROUP BY method;`
8. **Edge-to-Cloud Rollup Sync (Đo lường thời gian xuất nén Parquet ZSTD gửi về Cloud):**  
   So sánh DuckDB Native C++ Zero-Copy Rollup (`COPY ... TO PARQUET ZSTD`) đối đầu với SQLite Python Pipeline (Query $\rightarrow$ Python Memory $\rightarrow$ PyArrow $\rightarrow$ Parquet).

> 📖 **Xem tài liệu giải trình phản biện khoa học chi tiết:** [`docs/LUAN_DIEM_KHOA_HOC_VA_PHAN_BIEN.md`](docs/LUAN_DIEM_KHOA_HOC_VA_PHAN_BIEN.md)

---

## 🌐 CƠ CHẾ TIẾT KIỆM BĂNG THÔNG CLOUD (ROLLUP & PARQUET SYNC)

Một trong những đóng góp quan trọng của đề tài là **tối ưu hóa truyền dẫn dữ liệu từ biên lên mây**:

### 1. Công thức tính % tiết kiệm băng thông
Được cài đặt trong [`CloudSyncer`](file:///C:/WorkSpace/master/ky4/02_CSDLNC/edge-log-analytics/client/core/cloud_syncer.py):

$$\text{Tỷ lệ tiết kiệm (\%)} = \frac{\text{Raw Bytes} - \text{Parquet Bytes}}{\text{Raw Bytes}} \times 100\%$$

* **Raw Bytes:** $\text{Tổng số log thô} \times 200 \text{ bytes}$ (kích thước trung bình của một bản ghi JSON log thô).
* **Parquet Bytes:** Dung lượng file Parquet đã nén ZSTD tạo ra bởi DuckDB.

### 2. Truy vấn Rollup tự động (DuckDB Native Zero-Copy)
Cứ mỗi 30 giây, tiến trình nền tự động thực thi:
```sql
COPY (
    SELECT 
        time_bucket(INTERVAL '15 MINUTES', timestamp) AS window_start,
        client_ip,
        method,
        attack_type,
        COUNT(*) AS total_requests,
        COUNT(*) FILTER (WHERE label = 'attack') AS attack_requests,
        COUNT(*) FILTER (WHERE status_code >= 400) AS error_requests,
        ROUND(AVG(bytes_sent), 2) AS avg_bytes,
        ROUND(QUANTILE_CONT(bytes_sent, 0.99), 2) AS p99_bytes,
        ROUND(AVG(latency_ms), 2) AS avg_latency,
        ROUND(QUANTILE_CONT(latency_ms, 0.99), 2) AS p99_latency
    FROM edge_logs
    GROUP BY ALL
) TO 'data/parquet_rollups/rollup.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
```
File tóm tắt này lập tức được gửi qua HTTP POST tới máy chủ Cloud Receiver.

### 3. Kết quả đo kiểm thực tế
- Với **40.000 log thô** (~8.2 MB JSON), file Parquet Rollup sau khi nén chỉ còn **~550 KB**.
- Mức tiết kiệm băng thông đạt **93.1% đến 99.7%**, giúp hệ thống vận hành bền bỉ trên các đường truyền di động 4G hạn chế.

---

## 🖥 HỆ THỐNG GIÁM SÁT & BẢNG ĐIỀU KHIỂN

### 1. Grafana Central Fleet Dashboard (`http://localhost:3000`)
Dashboard giám sát tập trung toàn bộ các Gateways với 8 Panels thời gian thực:
1. **Tổng Raw Logs Đã Xử Lý Tại Biên:** Đếm tổng số log toàn bộ cụm đã tiêu thụ.
2. **Tiết Kiệm Băng Thông Cloud (Parquet):** Tỷ lệ nén truyền dẫn trung bình (~99.7%).
3. **Sự Cố Khẩn Cấp Đang Kích Hoạt:** Đếm số cảnh báo đang vi phạm ngưỡng trong cửa sổ 60s.
4. **Số Lượng Edge Gateways Online:** Số node Gateway đang hoạt động.
5. **Tỷ Lệ Lỗi % Cửa Sổ Trượt 60s:** Biểu đồ đường phân tích lỗi HTTP 4xx/5xx theo từng node.
6. **Độ Trễ Phân Vị P99 (ms):** Theo dõi độ trễ đỉnh điểm tính bằng DuckDB.
7. **Mức Tiêu Thụ RAM Thực Tế (Giới Hạn Cứng 512MB):** Thanh Bar Gauge giám sát tài nguyên bộ nhớ từng container.
8. **Mức Độ Tải CPU (%) Của Từng Thiết Bị Biên:** Biểu đồ tải vi xử lý.

### 2. Local Web UI Dashboard (`http://localhost:8001`)
Giao diện Dark Mode tại chỗ dành cho kỹ thuật viên tại trạm biên:
- Kết nối trực tiếp qua **WebSocket** (`/ws/stream`), cập nhật biểu đồ mỗi 1 giây.
- Xem danh sách cảnh báo sự cố cục bộ tức thì.
- Nút bấm chạy Benchmark và xem biểu đồ so sánh trực tiếp trên web.

---

## 📡 DANH MỤC API ENDPOINTS

### Edge Gateway (FastAPI)
| Endpoint | Phương thức | Mô tả |
| :--- | :--- | :--- |
| `/` | `GET` | Giao diện Local Web Dashboard |
| `/metrics` | `GET` | Xuất khẩu metrics chuẩn Prometheus (OpenMetrics) |
| `/ws/stream` | `WebSocket` | Kênh truyền thông tin metrics và cảnh báo thời gian thực |
| `/api/trigger-rollup` | `POST` | Kích hoạt xuất bản tóm tắt Parquet thủ công |
| `/api/run-benchmark` | `POST` | Kích hoạt kịch bản đo kiểm benchmark (tham số: `rows`) |
| `/api/benchmark-results` | `GET` | Lấy dữ liệu kết quả đo kiểm dạng JSON |
| `/api/benchmark-image` | `GET` | Xem ảnh biểu đồ benchmark đã tạo |

### Cloud Receiver (FastAPI)
| Endpoint | Phương thức | Mô tả |
| :--- | :--- | :--- |
| `/` | `GET` | Kiểm tra trạng thái máy chủ Cloud Receiver |
| `/api/upload-parquet` | `POST` | Tiếp nhận file Parquet nén upload từ các Edge Gateways |

---

## 👥 THÔNG TIN TÁC GIẢ & BẢN QUYỀN
* **Đơn vị:** Đại học Công nghệ Thông tin (UIT - ĐHQG-HCM)
* **Khoa:** Khoa Hệ thống Thông tin / Khoa học Dữ liệu
* **Học viên thực hiện:** Học viên Cao học ngành CNTT
* **Giấy phép:** MIT License
