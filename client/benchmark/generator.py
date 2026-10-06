import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
except Exception:
    pass
import os
import glob
import random
import datetime
import pyarrow as pa
from typing import List, Dict, Any, Optional

CLIENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cấu hình danh mục mô phỏng tập dữ liệu Web Server Access Logs (Kaggle Mahendra Data)
ENDPOINTS_BENIGN = [
    "/product/14926",
    "/product/10421",
    "/product/20914",
    "/category/electronics",
    "/category/home-appliances",
    "/category/books",
    "/cart/view",
    "/cart/add_item",
    "/checkout/payment",
    "/user/profile",
    "/static/css/theme.min.css",
    "/static/js/bundle.min.js",
    "/static/images/logo.png",
    "/search?category=all&page=1"
]

ATTACK_PAYLOADS = [
    ("/product?id=1' UNION SELECT null,table_name,column_name FROM information_schema.columns--", "sqli"),
    ("/search?keyword=' OR '1'='1' --", "sqli"),
    ("/api/v1/auth/login?user=admin'--", "sqli"),
    ("/cgi-bin/test.sh?cmd=cat%20/etc/passwd", "rce"),
    ("/endpoint?eval=system('id')", "rce"),
    ("/search?q=<script>alert('XSS_PAYLOAD')</script>", "xss"),
    ("/profile/comment?body=<img src=x onerror=alert(1)>", "xss"),
    ("/view_file?path=../../../../etc/shadow", "lfi"),
    ("/include.php?page=php://input", "lfi"),
    ("/admin/super-secret-config.php", "brute_force"),
    ("/wp-admin/install.php", "brute_force")
]

METHODS = ["GET", "GET", "GET", "POST", "GET", "POST", "PUT", "DELETE"]
IP_SUBNETS = [
    "207.46.13.", "157.55.39.", "66.249.66.", "180.76.15.", "114.119.130.",
    "192.168.1.", "10.0.4.", "172.16.0.", "8.8.8.", "1.1.1."
]

REFERERS = [
    "https://shop.uit.edu.vn/",
    "https://google.com/search",
    "https://bing.com/",
    "-",
    "-"
]

class KaggleCSVStreamer:
    """Bộ đọc luồng dữ liệu hiệu năng cao từ file CSV Kaggle gốc 2.86 GB"""
    def __init__(self, csv_path: str, batch_size: int = 10000):
        import duckdb
        self.csv_path = csv_path.replace("\\", "/")
        self.batch_size = batch_size
        self.con = duckdb.connect()
        query = f"""
            SELECT 
                CAST(time AS TIMESTAMP) AS timestamp,
                CAST(ip AS VARCHAR) AS client_ip,
                CAST(method AS VARCHAR) AS method,
                CAST(url AS VARCHAR) AS endpoint,
                CAST(COALESCE(status, 200) AS INTEGER) AS status_code,
                CAST(COALESCE(size, 0) AS BIGINT) AS bytes_sent,
                CAST(50.0 + (COALESCE(size, 1000) % 500) AS FLOAT) AS latency_ms,
                CASE WHEN CAST(label AS VARCHAR) IN ('1', 'attack') THEN 'attack' ELSE 'benign' END AS label,
                CAST(COALESCE(type, 'benign') AS VARCHAR) AS attack_type,
                CAST(COALESCE(referrer, '-') AS VARCHAR) AS referer
            FROM read_csv_auto('{self.csv_path}', ignore_errors=true)
        """
        self.reader = self.con.execute(query).to_arrow_reader(batch_size=batch_size)

    def next_batch(self, count: int) -> List[Dict[str, Any]]:
        try:
            rb = self.reader.read_next_batch()
            tbl = pa.Table.from_batches([rb])
            return tbl.to_pylist()
        except StopIteration:
            return []
        except Exception as e:
            print(f"[KaggleCSVStreamer] Lỗi đọc batch: {e}")
            return []

    def close(self):
        try:
            self.con.close()
        except Exception:
            pass

_STREAMER: Optional[KaggleCSVStreamer] = None
_LAST_BATCH_SIZE: Optional[int] = None

def find_kaggle_csv() -> Optional[str]:
    """Tìm kiếm file CSV của dataset Kaggle trong thư mục data/"""
    candidates = [
        os.path.join(CLIENT_DIR, "data", "web_server_access_logs.csv"),
        "client/data/web_server_access_logs.csv",
        "data/web_server_access_logs.csv"
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 50000000: # Lớn hơn 50MB là file thật 2.86GB
            return os.path.abspath(p)
    return None

def reset_streamer(batch_size: int = 10000):
    global _STREAMER, _LAST_BATCH_SIZE
    if _STREAMER:
        _STREAMER.close()
    csv_file = find_kaggle_csv()
    if csv_file:
        print(f"[generator] -> Đang đọc trực tiếp từ Dataset Kaggle thật: {csv_file}")
        _STREAMER = KaggleCSVStreamer(csv_file, batch_size=batch_size)
        _LAST_BATCH_SIZE = batch_size
    else:
        _STREAMER = None

def generate_log_batch(count: int, start_time: datetime.datetime, device_count: int = 50, anomaly_rate: float = 0.05) -> List[Dict[str, Any]]:
    """
    Cung cấp batch log:
    - Nếu có file CSV thật từ Kaggle (2.86 GB), đọc tuần tự từng batch siêu tốc từ file thật.
    - Nếu không có, tự động sinh batch mô phỏng chuẩn xác định dạng Kaggle.
    """
    global _STREAMER, _LAST_BATCH_SIZE
    csv_file = find_kaggle_csv()
    if csv_file:
        if _STREAMER is None or _LAST_BATCH_SIZE != count:
            reset_streamer(batch_size=count)
        if _STREAMER:
            batch = _STREAMER.next_batch(count)
            if batch and len(batch) > 0:
                return batch

    # Chế độ sinh mô phỏng nếu file CSV kết thúc hoặc không tìm thấy
    records = []
    current_time = start_time
    time_step = datetime.timedelta(milliseconds=max(1, 1000 // max(count, 1)))

    for i in range(count):
        is_attack = random.random() < anomaly_rate
        subnet = random.choice(IP_SUBNETS)
        client_ip = f"{subnet}{random.randint(1, device_count * 2)}"

        if is_attack:
            endpoint, attack_type = random.choice(ATTACK_PAYLOADS)
            label = "attack"
            method = random.choice(["GET", "POST"])
            status_code = random.choice([400, 403, 404, 500, 503])
            bytes_sent = random.randint(350, 4500)
            latency_ms = round(random.uniform(500.0, 3500.0), 2)
        else:
            endpoint = random.choice(ENDPOINTS_BENIGN)
            attack_type = "benign"
            label = "benign"
            method = random.choice(METHODS)
            status_code = random.choices([200, 302, 304, 404], weights=[0.85, 0.08, 0.05, 0.02])[0]
            bytes_sent = random.randint(1200, 68000)
            latency_ms = round(random.uniform(15.0, 350.0), 2)

        records.append({
            "timestamp": current_time,
            "client_ip": client_ip,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "bytes_sent": bytes_sent,
            "latency_ms": latency_ms,
            "label": label,
            "attack_type": attack_type,
            "referer": random.choice(REFERERS)
        })
        current_time += time_step

    return records
