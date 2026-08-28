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
                device_id TEXT,
                log_level TEXT,
                service_name TEXT,
                cpu_usage REAL,
                memory_free_mb INTEGER,
                latency_ms REAL,
                status_code INTEGER,
                message TEXT
            );
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON edge_logs(timestamp);")
        self.conn.commit()

    def insert_records(self, records: List[Dict[str, Any]]):
        if not records:
            return
        data = [
            (
                str(r["timestamp"]),
                r["device_id"],
                r["log_level"],
                r["service_name"],
                r["cpu_usage"],
                r["memory_free_mb"],
                r["latency_ms"],
                r["status_code"],
                r["message"]
            )
            for r in records
        ]
        with self.conn:
            self.conn.executemany("""
                INSERT INTO edge_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
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

    def close(self):
        self.conn.close()
