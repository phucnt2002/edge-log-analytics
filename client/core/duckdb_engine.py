import os
import duckdb
import pyarrow as pa
from typing import List, Dict, Any, Optional

class DuckDBEngine:
    def __init__(self, db_path: str = "data/edge_logs.duckdb", max_memory_mb: int = 256, threads: int = 4):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self.conn.execute(f"SET max_memory = '{max_memory_mb}MB';")
        self.conn.execute(f"SET threads = {threads};")
        self.conn.execute("SET preserve_insertion_order = false;")
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edge_logs (
                timestamp TIMESTAMP,
                device_id VARCHAR,
                log_level VARCHAR,
                service_name VARCHAR,
                cpu_usage FLOAT,
                memory_free_mb INTEGER,
                latency_ms FLOAT,
                status_code INTEGER,
                message VARCHAR
            );
        """)

    def insert_arrow_batch(self, table: pa.Table):
        self.conn.register("arrow_batch", table)
        self.conn.execute("INSERT INTO edge_logs SELECT * FROM arrow_batch;")
        self.conn.unregister("arrow_batch")

    def insert_records(self, records: List[Dict[str, Any]]):
        if not records:
            return
        table = pa.Table.from_pylist(records)
        self.insert_arrow_batch(table)

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> List[tuple]:
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def get_sliding_window_metrics(self, window_seconds: int = 60) -> Dict[str, Any]:
        query = f"""
            SELECT 
                COUNT(*) AS total_logs,
                COUNT(*) FILTER (WHERE log_level IN ('ERROR', 'CRITICAL')) AS error_count,
                ROUND(AVG(cpu_usage), 2) AS avg_cpu,
                ROUND(AVG(latency_ms), 2) AS avg_latency,
                ROUND(QUANTILE_CONT(latency_ms, 0.95), 2) AS p95_latency,
                ROUND(QUANTILE_CONT(latency_ms, 0.99), 2) AS p99_latency,
                COUNT(DISTINCT device_id) AS active_devices
            FROM edge_logs
            WHERE timestamp >= (SELECT MAX(timestamp) FROM edge_logs) - INTERVAL '{window_seconds} SECONDS';
        """
        res = self.conn.execute(query).fetchone()
        if not res or res[0] == 0:
            return {
                "total_logs": 0, "error_count": 0, "error_rate_pct": 0.0,
                "avg_cpu": 0.0, "avg_latency": 0.0, "p95_latency": 0.0, "p99_latency": 0.0,
                "active_devices": 0
            }
        total = res[0]
        err_count = res[1] or 0
        err_rate = round((err_count / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "total_logs": total,
            "error_count": err_count,
            "error_rate_pct": err_rate,
            "avg_cpu": res[2] or 0.0,
            "avg_latency": res[3] or 0.0,
            "p95_latency": res[4] or 0.0,
            "p99_latency": res[5] or 0.0,
            "active_devices": res[6] or 0
        }

    def export_parquet_rollup(self, output_path: str, interval_minutes: int = 15) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        query = f"""
            COPY (
                SELECT 
                    time_bucket(INTERVAL '{interval_minutes} MINUTES', timestamp) AS window_start,
                    device_id,
                    service_name,
                    COUNT(*) AS total_events,
                    COUNT(*) FILTER (WHERE log_level IN ('ERROR', 'CRITICAL')) AS error_events,
                    ROUND(AVG(cpu_usage), 2) AS avg_cpu,
                    ROUND(AVG(latency_ms), 2) AS avg_latency,
                    ROUND(QUANTILE_CONT(latency_ms, 0.99), 2) AS p99_latency
                FROM edge_logs
                GROUP BY ALL
            ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD);
        """
        self.conn.execute(query)
        return output_path

    def get_total_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM edge_logs;").fetchone()[0]

    def close(self):
        self.conn.close()
