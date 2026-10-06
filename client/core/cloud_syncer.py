import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import datetime
from core.duckdb_engine import DuckDBEngine

class CloudSyncer:
    def __init__(self, duck_engine: DuckDBEngine, export_dir: str = "data/parquet_rollups"):
        self.duck = duck_engine
        self.export_dir = export_dir
        self.latest_bandwidth_saved_pct = 0.0
        os.makedirs(self.export_dir, exist_ok=True)
        self._calculate_initial_savings()

    def _calculate_initial_savings(self):
        """Tính toán tỷ lệ tiết kiệm sơ bộ nếu đã có file rollup trong thư mục"""
        try:
            files = [os.path.join(self.export_dir, f) for f in os.listdir(self.export_dir) if f.endswith(".parquet")]
            if files:
                latest_file = max(files, key=os.path.getctime)
                parquet_bytes = os.path.getsize(latest_file)
                raw_count = self.duck.get_total_count()
                raw_bytes = max(raw_count * 200, parquet_bytes)
                self.latest_bandwidth_saved_pct = round(((raw_bytes - parquet_bytes) / raw_bytes) * 100, 1)
        except Exception:
            self.latest_bandwidth_saved_pct = 0.0

    def trigger_rollup_export(self, interval_minutes: int = 15) -> str:
        node_id = os.getenv("NODE_ID", "edge")
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.export_dir, f"rollup_{node_id}_{now_str}.parquet")
        self.duck.export_parquet_rollup(file_path, interval_minutes=interval_minutes)
        size_kb = os.path.getsize(file_path) / 1024.0
        
        # Tính toán dung lượng log thô tương đương (trung bình 200 bytes/log thô JSON)
        raw_count = self.duck.get_total_count()
        raw_bytes = max(raw_count * 200, os.path.getsize(file_path))
        parquet_bytes = os.path.getsize(file_path)
        if raw_bytes > 0:
            self.latest_bandwidth_saved_pct = round(((raw_bytes - parquet_bytes) / raw_bytes) * 100, 1)

        print(f"[CloudSyncer] Đã xuất bản tóm tắt Parquet nén: {file_path} ({size_kb:.1f} KB) - Tiết kiệm: {self.latest_bandwidth_saved_pct}%")

        # Tự động gửi file Parquet tóm tắt lên Cloud Receiver nếu có cấu hình
        receiver_url = os.getenv("CLOUD_RECEIVER_URL", "http://cloud-receiver:5000/api/upload-parquet")
        if receiver_url:
            try:
                import requests
                with open(file_path, "rb") as f:
                    requests.post(receiver_url, files={"file": (os.path.basename(file_path), f)}, timeout=3)
            except Exception:
                pass

        return file_path
