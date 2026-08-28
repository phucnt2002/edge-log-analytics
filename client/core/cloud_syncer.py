import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import datetime
from core.duckdb_engine import DuckDBEngine

class CloudSyncer:
    def __init__(self, duck_engine: DuckDBEngine, export_dir: str = "data/parquet_rollups"):
        self.duck = duck_engine
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def trigger_rollup_export(self, interval_minutes: int = 15) -> str:
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.export_dir, f"rollup_{now_str}.parquet")
        self.duck.export_parquet_rollup(file_path, interval_minutes=interval_minutes)
        size_kb = os.path.getsize(file_path) / 1024.0
        print(f"[CloudSyncer] Đã xuất bản tóm tắt Parquet nén: {file_path} ({size_kb:.1f} KB)")
        return file_path
