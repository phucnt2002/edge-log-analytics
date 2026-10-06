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
                client_ip VARCHAR,
                method VARCHAR,
                endpoint VARCHAR,
                status_code INTEGER,
                bytes_sent BIGINT,
                latency_ms FLOAT,
                label VARCHAR,
                attack_type VARCHAR,
                referer VARCHAR
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
                COUNT(*) FILTER (WHERE label = 'attack') AS attack_count,
                COUNT(*) FILTER (WHERE status_code >= 400) AS error_count,
                ROUND(AVG(bytes_sent), 2) AS avg_bytes,
                ROUND(AVG(latency_ms), 2) AS avg_latency,
                ROUND(QUANTILE_CONT(latency_ms, 0.95), 2) AS p95_latency,
                ROUND(QUANTILE_CONT(latency_ms, 0.99), 2) AS p99_latency,
                ROUND(QUANTILE_CONT(bytes_sent, 0.99), 2) AS p99_bytes,
                COUNT(DISTINCT client_ip) AS active_ips
            FROM edge_logs
            WHERE timestamp >= (SELECT MAX(timestamp) FROM edge_logs) - INTERVAL '{window_seconds} SECONDS';
        """
        res = self.conn.execute(query).fetchone()
        if not res or res[0] == 0:
            return {
                "total_logs": 0, "attack_count": 0, "attack_rate_pct": 0.0,
                "error_count": 0, "error_rate_pct": 0.0,
                "avg_bytes": 0.0, "avg_latency": 0.0, "p95_latency": 0.0, "p99_latency": 0.0,
                "p99_bytes": 0.0, "active_ips": 0, "avg_cpu": 0.0
            }
        total = res[0]
        attack_count = res[1] or 0
        err_count = res[2] or 0
        attack_rate = round((attack_count / total) * 100.0, 2) if total > 0 else 0.0
        err_rate = round((err_count / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "total_logs": total,
            "attack_count": attack_count,
            "attack_rate_pct": attack_rate,
            "error_count": err_count,
            "error_rate_pct": err_rate,
            "avg_bytes": res[3] or 0.0,
            "avg_latency": res[4] or 0.0,
            "p95_latency": res[5] or 0.0,
            "p99_latency": res[6] or 0.0,
            "p99_bytes": res[7] or 0.0,
            "active_ips": res[8] or 0,
            "avg_cpu": attack_rate  # Ánh xạ tỷ lệ tấn công hiển thị trên dashboard
        }

    def export_parquet_rollup(self, output_path: str, interval_minutes: int = 15) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        query = f"""
            COPY (
                SELECT 
                    time_bucket(INTERVAL '{interval_minutes} MINUTES', timestamp) AS window_start,
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
            ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD);
        """
        self.conn.execute(query)
        return output_path

    def get_total_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM edge_logs;").fetchone()[0]

    def close(self):
        self.conn.close()
