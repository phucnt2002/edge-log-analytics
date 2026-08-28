import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import time
import json
import psutil
import datetime
import pyarrow as pa
from typing import Dict, Any

from core.duckdb_engine import DuckDBEngine
from core.sqlite_engine import SQLiteEngine
from benchmark.generator import generate_log_batch

def run_benchmark(total_rows: int = 100000, batch_size: int = 5000) -> Dict[str, Any]:
    print(f"====================================================================")
    print(f"  BẮT ĐẦU BENCHMARK ĐỐI CHUẨN: DUCKDB vs SQLITE ({total_rows:,} ROWS)  ")
    print(f"====================================================================\n")

    data_dir = "data/benchmark"
    os.makedirs(data_dir, exist_ok=True)
    duck_path = os.path.join(data_dir, "bench.duckdb")
    sqlite_path = os.path.join(data_dir, "bench.sqlite")

    for p in [duck_path, sqlite_path, sqlite_path + "-wal", sqlite_path + "-shm"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    duck = DuckDBEngine(db_path=duck_path, max_memory_mb=256, threads=4)
    sqlite = SQLiteEngine(db_path=sqlite_path)

    print("[*] 1/3: Đang sinh dữ liệu và đo lường tốc độ nạp (Ingestion)...")
    start_time = datetime.datetime(2026, 8, 27, 8, 0, 0)
    
    t0 = time.perf_counter()
    for offset in range(0, total_rows, batch_size):
        batch = generate_log_batch(batch_size, start_time + datetime.timedelta(seconds=offset))
        table = pa.Table.from_pylist(batch)
        duck.insert_arrow_batch(table)
    t_duck_ingest = time.perf_counter() - t0
    duck_ingest_rate = total_rows / max(t_duck_ingest, 0.001)
    print(f"   -> DuckDB: {duck_ingest_rate:,.0f} rows/s (Thời gian: {t_duck_ingest:.2f}s)")

    t0 = time.perf_counter()
    for offset in range(0, total_rows, batch_size):
        batch = generate_log_batch(batch_size, start_time + datetime.timedelta(seconds=offset))
        sqlite.insert_records(batch)
    t_sqlite_ingest = time.perf_counter() - t0
    sqlite_ingest_rate = total_rows / max(t_sqlite_ingest, 0.001)
    print(f"   -> SQLite: {sqlite_ingest_rate:,.0f} rows/s (Thời gian: {t_sqlite_ingest:.2f}s)")

    print("\n[*] 2/3: Đang đo lường dung lượng lưu trữ trên ổ đĩa...")
    duck.conn.execute("CHECKPOINT;")
    duck_size_mb = os.path.getsize(duck_path) / (1024.0 * 1024.0)
    
    sqlite.conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    sqlite_size_mb = os.path.getsize(sqlite_path) / (1024.0 * 1024.0)
    compression_ratio = sqlite_size_mb / max(duck_size_mb, 0.01)

    print(f"   -> Dung lượng DuckDB (Columnar nén) : {duck_size_mb:.2f} MB")
    print(f"   -> Dung lượng SQLite (Row-based B-Tree): {sqlite_size_mb:.2f} MB")
    print(f"   -> Tiết kiệm không gian đĩa         : {((sqlite_size_mb - duck_size_mb)/sqlite_size_mb)*100:.1f}%")

    print("\n[*] 3/3: Đang thực thi bộ 5 truy vấn phân tích chuyên sâu (Mỗi query 10 lần)...")
    
    queries = {
        "Q1_Count_Filter": {
            "name": "Q1: Point Filter & Count (Lọc log lỗi)",
            "duck_sql": "SELECT COUNT(*) FROM edge_logs WHERE log_level IN ('ERROR', 'CRITICAL');",
            "sqlite_sql": "SELECT COUNT(*) FROM edge_logs WHERE log_level IN ('ERROR', 'CRITICAL');"
        },
        "Q2_Group_By": {
            "name": "Q2: Multi-dim Group By (Thống kê theo thiết bị)",
            "duck_sql": "SELECT device_id, log_level, COUNT(*), AVG(latency_ms) FROM edge_logs GROUP BY device_id, log_level;",
            "sqlite_sql": "SELECT device_id, log_level, COUNT(*), AVG(latency_ms) FROM edge_logs GROUP BY device_id, log_level;"
        },
        "Q3_Window_Metrics": {
            "name": "Q3: Heavy Multi-Agg (Tổng hợp đa chỉ số)",
            "duck_sql": """
                SELECT COUNT(*), AVG(cpu_usage), AVG(latency_ms), MAX(latency_ms), MIN(memory_free_mb)
                FROM edge_logs
                WHERE cpu_usage > 50.0;
            """,
            "sqlite_sql": """
                SELECT COUNT(*), AVG(cpu_usage), AVG(latency_ms), MAX(latency_ms), MIN(memory_free_mb)
                FROM edge_logs
                WHERE cpu_usage > 50.0;
            """
        },
        "Q4_Percentile_Math": {
            "name": "Q4: P95 & P99 Math (Phân vị độ trễ)",
            "duck_sql": """
                SELECT QUANTILE_CONT(latency_ms, 0.95), QUANTILE_CONT(latency_ms, 0.99)
                FROM edge_logs;
            """,
            "sqlite_sql": """
                SELECT latency_ms FROM edge_logs ORDER BY latency_ms LIMIT 1 OFFSET (SELECT CAST(COUNT(*)*0.99 AS INT) FROM edge_logs);
            """
        },
        "Q5_Pattern_Match": {
            "name": "Q5: Text Pattern Search (Tìm kiếm chuỗi message)",
            "duck_sql": "SELECT COUNT(*) FROM edge_logs WHERE message LIKE '%timeout%';",
            "sqlite_sql": "SELECT COUNT(*) FROM edge_logs WHERE message LIKE '%timeout%';"
        }
    }

    query_results = {}
    N_RUNS = 7

    for qkey, qdata in queries.items():
        duck.conn.execute(qdata["duck_sql"]).fetchall()
        sqlite.execute_query(qdata["sqlite_sql"])

        duck_times = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            duck.conn.execute(qdata["duck_sql"]).fetchall()
            duck_times.append((time.perf_counter() - t0) * 1000.0)
        avg_duck = sum(duck_times) / len(duck_times)

        sqlite_times = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            sqlite.execute_query(qdata["sqlite_sql"])
            sqlite_times.append((time.perf_counter() - t0) * 1000.0)
        avg_sqlite = sum(sqlite_times) / len(sqlite_times)

        speedup = avg_sqlite / max(avg_duck, 0.001)
        query_results[qkey] = {
            "name": qdata["name"],
            "duckdb_ms": round(avg_duck, 2),
            "sqlite_ms": round(avg_sqlite, 2),
            "speedup": round(speedup, 1)
        }
        print(f"   • {qdata['name']}")
        print(f"     DuckDB: {avg_duck:.2f} ms | SQLite: {avg_sqlite:.2f} ms | Speedup: {speedup:.1f}x")

    results = {
        "total_rows": total_rows,
        "timestamp": datetime.datetime.now().isoformat(),
        "ingestion": {
            "duckdb_rows_per_sec": round(duck_ingest_rate, 0),
            "sqlite_rows_per_sec": round(sqlite_ingest_rate, 0),
            "duckdb_time_sec": round(t_duck_ingest, 2),
            "sqlite_time_sec": round(t_sqlite_ingest, 2)
        },
        "storage": {
            "duckdb_size_mb": round(duck_size_mb, 2),
            "sqlite_size_mb": round(sqlite_size_mb, 2),
            "space_saving_pct": round(((sqlite_size_mb - duck_size_mb)/sqlite_size_mb)*100, 1),
            "compression_ratio": round(compression_ratio, 2)
        },
        "queries": query_results
    }

    result_json_path = "data/benchmark_results.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    duck.close()
    sqlite.close()
    
    print(f"\n[✓] Hoàn tất Benchmark! Kết quả đã lưu tại {result_json_path}")
    return results

if __name__ == "__main__":
    rows = 100000
    if len(sys.argv) > 1:
        rows = int(sys.argv[1])
    run_benchmark(total_rows=rows)
