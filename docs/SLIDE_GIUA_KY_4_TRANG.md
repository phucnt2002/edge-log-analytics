# SLIDE BÁO CÁO GIỮA KỲ (4 SLIDES)
**HỌC PHẦN: CƠ SỞ DỮ LIỆU NÂNG CAO (CSDLNC)**

---

## [SLIDE 1] GIỚI THIỆU ĐỀ TÀI & ĐẶT VẤN ĐỀ

* **Tên đề tài:** Phân tích dữ liệu nhật ký IoT thời gian thực tại thiết bị biên: Đối chuẩn hiệu năng DuckDB (Columnar OLAP) và SQLite (Row-oriented OLTP).
* **Học viên thực hiện:** [Họ và tên học viên] — Lớp: CSDL Nâng cao (Kỳ 4).

### 1. Thực trạng & Thách thức kiến trúc Cloud tập trung
* Hàng triệu bản ghi IoT thô đẩy liên tục lên Cloud $\rightarrow$ Tắc nghẽn băng thông mạng, chi phí lưu trữ và truyền dẫn (egress cost) rất lớn.
* Độ trễ xử lý tập trung cao $\rightarrow$ Không đáp ứng yêu cầu phát hiện bất thường và cảnh báo tức thì khi xảy ra lỗi.
* Nguy cơ gián đoạn giám sát khi mạng Internet chập chờn hoặc đứt kết nối (Network Partition).

### 2. Đề xuất giải pháp: In-Situ Edge Analytics
* Chuyển dịch tính toán phân tích (OLAP) xuống thực thi tại chỗ (In-Situ) ngay trên thiết bị biên (Edge Gateway).
* Ứng dụng **DuckDB**: Hệ quản trị CSDL nhúng dạng cột (Columnar Engine) với cơ chế Vectorized Execution siêu nhẹ, không cần cài đặt server phức tạp.
* **Sliding Window Analytics:** Liên tục phân tích trong cửa sổ trượt 60 giây và kích hoạt cảnh báo ngưỡng tức thì cục bộ.
* **Hierarchical Parquet Rollup:** Định kỳ nén log tóm tắt thành tệp `.parquet` (ZSTD), tiết kiệm trên 90% băng thông mạng.

---

## [SLIDE 2] THIẾT KẾ KIẾN TRÚC & PIPELINE XỬ LÝ DỮ LIỆU

### 1. Mô hình phân tầng Edge – Cloud
* **Tầng Biên (Edge Gateways - VM 1):** Cụm 5 trạm biên chạy container độc lập (giới hạn 512MB RAM/node), tiếp nhận log thời gian thực, lưu trữ cục bộ, mở cổng trích xuất Prometheus `/metrics` và Web Dashboard WebSocket.
* **Tầng Đám mây (Cloud Monitoring - VM 2):** Prometheus Scraper thu thập số liệu phân tán; Grafana quản trị tập trung toàn bộ đội tàu thiết bị; Cloud Receiver tiếp nhận tệp Parquet nén.

### 2. Pipeline xử lý dữ liệu tại biên (In-Situ Pipeline)
1. **Async Ring Buffer (Micro-batching):** Đệm hàng đợi bất đồng bộ (`asyncio.Queue`) chuyển đổi zero-copy sang **Apache Arrow Table**, nạp vào DuckDB với tốc độ cao.
2. **Stream Analyzer (Sliding Window):** Chu kỳ 1 giây quét cửa sổ trượt 60 giây, tính toán P95, P99 Latency và tỉ lệ lỗi qua toán tử `QUANTILE_CONT`.
3. **Local Alert Manager:** Đánh giá biểu thức điều kiện động theo `rules.json`, kích hoạt cảnh báo ngay lập tức qua WebSocket.
4. **Hierarchical Parquet Rollup:** Định kỳ 15 phút nén dữ liệu phân vùng thành file `.parquet` (ZSTD), đẩy về kho dữ liệu Cloud.

---

## [SLIDE 3] KẾT QUẢ ĐỐI CHUẨN THỰC NGHIỆM: DUCKDB VS SQLITE

*Thử nghiệm đo kiểm trên 100.000 – 1.000.000 bản ghi, cấu hình phần cứng biên giới hạn 256MB RAM.*

### 1. Bảng số liệu đối chuẩn hiệu năng nạp và đĩa

| Tiêu chí đối chuẩn | SQLite (B-Tree + WAL) | DuckDB (1 Thread) | DuckDB (4 Threads) | Hiệu năng vượt trội |
| :--- | :---: | :---: | :---: | :---: |
| **Tốc độ nạp (Ingestion)** | 31.000 rows/s | 82.000 rows/s | **105.000 rows/s** | **DuckDB nhanh 3.39x** |
| **Dung lượng CSDL trên đĩa** | 16.50 MB | 4.25 MB | **4.25 MB** | **DuckDB giảm 74.2%** |
| **Tiết kiệm băng thông Cloud** | *Không áp dụng* | > 91.5% | **> 91.5%** | Tiết kiệm chi phí truyền tải |

### 2. Tốc độ thực thi 5 câu truy vấn phân tích (Execution Time)
* **Q1 (Point Filter & Count):** DuckDB nhanh hơn **13.8x** (0.9 ms vs 12.4 ms).
* **Q2 (Multi-dim Group By):** DuckDB nhanh hơn **40.5x** (1.2 ms vs 48.6 ms).
* **Q3 (Heavy Multi-Agg):** DuckDB nhanh hơn **40.1x** (0.8 ms vs 32.1 ms).
* **Q4 (P99 Latency Math - Phân vị):** DuckDB nhanh hơn **77.2x** (1.5 ms vs 115.8 ms nhờ tính toán trực tiếp trên vector số).
* **Q5 (Pattern Search - LIKE '%...%'):** DuckDB nhanh hơn **18.3x** (2.3 ms vs 42.0 ms).

---

## [SLIDE 4] KẾT LUẬN GIỮA KỲ & KẾ HOẠCH GIAI ĐOẠN TIẾP THEO

### 1. Kết luận rút ra từ nghiên cứu
* **Khẳng định tính ưu việt của CSDL dạng cột tại biên:** DuckDB chứng minh khả năng vượt trội so với SQLite trong các tác vụ phân tích, gom nhóm và tính toán phân vị trên phần cứng tài nguyên hạn chế.
* **Cơ chế nạp Arrow zero-copy** khắc phục hoàn toàn nhược điểm ghi đơn dòng truyền thống của các hệ CSDL cột.
* **Mô hình In-Situ kết hợp Parquet Rollup** là kiến trúc tối ưu để giải quyết triệt để bài toán thắt nút cổ chai băng thông trong hệ sinh thái IoT công nghiệp.

### 2. Kế hoạch hoàn thiện giai đoạn cuối kỳ
1. **Thực nghiệm phân mảnh mạng (Network Partitioning Test):** Kiểm tra khả năng tự lưu trữ, tự cảnh báo khi ngắt kết nối mạng và cơ chế đồng bộ bù lên Cloud khi có mạng trở lại.
2. **Đo lường chi tiết năng lượng & tải CPU liên tục:** Đo mức tiêu thụ RAM/CPU ổn định của tiến trình DuckDB khi nạp liên tục 24/7 trên phần cứng nhúng thực tế (Raspberry Pi/ARM64).
3. **Hoàn thiện đồ án:** Xuất bản báo cáo tổng kết và đóng gói mã nguồn mở của hệ thống.
