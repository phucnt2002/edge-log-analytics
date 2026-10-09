import os
import sqlite3
from typing import List, Dict, Any, Optional

class SQLiteEngine:
    def __init__(self, db_path: str = "data/edge_logs.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.execute("PRAGMA cache_size = -64000;")
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edge_logs (
                timestamp TEXT,
                client_ip TEXT,
                method TEXT,
                endpoint TEXT,
                status_code INTEGER,
                bytes_sent INTEGER,
                latency_ms REAL,
                label TEXT,
                attack_type TEXT,
                referer TEXT
            );
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON edge_logs(timestamp);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_label ON edge_logs(label);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_status ON edge_logs(status_code);")
        self.conn.commit()

    def insert_records(self, records: List[Dict[str, Any]]):
        if not records:
            return
        data = [
            (
                str(r["timestamp"]),
                r["client_ip"],
                r["method"],
                r["endpoint"],
                r["status_code"],
                r["bytes_sent"],
                r.get("latency_ms", 0.0),
                r["label"],
                r["attack_type"],
                r.get("referer", "-")
            )
            for r in records
        ]
        with self.conn:
            self.conn.executemany("""
                INSERT INTO edge_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, data)

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> List[tuple]:
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def get_total_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM edge_logs;")
        return cursor.fetchone()[0]

    def export_parquet_rollup(self, output_path: str, interval_minutes: int = 15) -> str:
        """Thực thi pipeline đồng bộ Rollup Parquet của SQLite (Query -> Python Memory -> PyArrow -> Parquet ZSTD)"""
        import pyarrow as pa
        import pyarrow.parquet as pq
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cursor = self.conn.cursor()
        query = """
            SELECT 
                client_ip,
                method,
                attack_type,
                COUNT(*) AS total_requests,
                SUM(CASE WHEN label = 'attack' THEN 1 ELSE 0 END) AS attack_requests,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS error_requests,
                ROUND(AVG(bytes_sent), 2) AS avg_bytes,
                ROUND(AVG(latency_ms), 2) AS avg_latency
            FROM edge_logs
            GROUP BY client_ip, method, attack_type;
        """
        rows = cursor.execute(query).fetchall()
        schema = pa.schema([
            ('client_ip', pa.string()),
            ('method', pa.string()),
            ('attack_type', pa.string()),
            ('total_requests', pa.int64()),
            ('attack_requests', pa.int64()),
            ('error_requests', pa.int64()),
            ('avg_bytes', pa.float64()),
            ('avg_latency', pa.float64())
        ])
        batch_dict = {
            'client_ip': [r[0] for r in rows],
            'method': [r[1] for r in rows],
            'attack_type': [r[2] for r in rows],
            'total_requests': [r[3] for r in rows],
            'attack_requests': [r[4] for r in rows],
            'error_requests': [r[5] for r in rows],
            'avg_bytes': [r[6] for r in rows],
            'avg_latency': [r[7] for r in rows]
        }
        table = pa.Table.from_pydict(batch_dict, schema=schema)
        pq.write_table(table, output_path, compression='zstd')
        return output_path

    def close(self):
        self.conn.close()
