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

def run_benchmark(total_rows: int = 100000, batch_size: int = None) -> Dict[str, Any]:
    if batch_size is None or batch_size == 5000:
        if total_rows >= 1000000:
            batch_size = 20000
        elif total_rows >= 500000:
            batch_size = 10000
        else:
            batch_size = 5000

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

    # Giới hạn bộ nhớ DuckDB cho benchmark phù hợp với phần cứng biên
    duck = DuckDBEngine(db_path=duck_path, max_memory_mb=64, threads=4)
    sqlite = SQLiteEngine(db_path=sqlite_path)

    # 1. ĐO LƯỜNG TỐC ĐỘ NẠP THUẦN TÚY (TIỀN CHUYỂN ĐỔI TỪNG BATCH ĐỂ TRÁNH TRÀN BỘ NHỚ BIÊN)
    print(f"[*] 1/4: Nạp đối chuẩn {total_rows:,} logs (Tách biệt thời gian sinh dữ liệu, kiểm soát RAM)...")
    start_time = datetime.datetime(2026, 8, 27, 8, 0, 0)
    
    t_duck_ingest = 0.0
    t_sqlite_ingest = 0.0

    for offset in range(0, total_rows, batch_size):
        # A. Sinh dữ liệu và chuẩn bị cấu trúc (HOÀN TOÀN NGOÀI ĐỒNG HỒ ĐO THỜI GIAN)
        batch = generate_log_batch(batch_size, start_time + datetime.timedelta(seconds=offset))
        tbl = pa.Table.from_pylist(batch)
        tuples = [
            (str(r["timestamp"]), r["device_id"], r["log_level"], r["service_name"],
             r["cpu_usage"], r["memory_free_mb"], r["latency_ms"], r["status_code"], r["message"])
            for r in batch
        ]

        # B. Bấm giờ NẠP THUẦN TÚY vào DuckDB
        t0 = time.perf_counter()
        duck.insert_arrow_batch(tbl)
        t_duck_ingest += time.perf_counter() - t0

        # C. Bấm giờ NẠP THUẦN TÚY vào SQLite
        t0 = time.perf_counter()
        with sqlite.conn:
            sqlite.conn.executemany("INSERT INTO edge_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", tuples)
        t_sqlite_ingest += time.perf_counter() - t0

        # Giải phóng rác RAM ngay trong vòng lặp
        del batch, tbl, tuples

    duck_ingest_rate = total_rows / max(t_duck_ingest, 0.001)
    sqlite_ingest_rate = total_rows / max(t_sqlite_ingest, 0.001)
    print(f"   -> DuckDB Ingestion: {duck_ingest_rate:,.0f} rows/s (Thời gian nạp thuần: {t_duck_ingest:.2f}s)")
    print(f"   -> SQLite Ingestion: {sqlite_ingest_rate:,.0f} rows/s (Thời gian nạp thuần: {t_sqlite_ingest:.2f}s)")

    # Tạo Index tối ưu cho SQLite để đảm bảo cạnh tranh công bằng
    print("   -> Đang tạo Index tối ưu trên SQLite (idx_logs_latency, idx_logs_level)...")
    sqlite.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_latency ON edge_logs(latency_ms);")
    sqlite.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON edge_logs(log_level);")
    sqlite.conn.commit()

    # 3. ĐO LƯỜNG DUNG LƯỢNG LƯU TRỮ TRÊN ĐĨA
    print("\n[*] 3/4: Đang đo lường dung lượng lưu trữ trên ổ đĩa...")
    duck.conn.execute("CHECKPOINT;")
    duck_size_mb = os.path.getsize(duck_path) / (1024.0 * 1024.0)
    
    sqlite.conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    sqlite_size_mb = os.path.getsize(sqlite_path) / (1024.0 * 1024.0)
    compression_ratio = sqlite_size_mb / max(duck_size_mb, 0.01)

    print(f"   -> Dung lượng DuckDB (Columnar nén) : {duck_size_mb:.2f} MB")
    print(f"   -> Dung lượng SQLite (Row-based B-Tree): {sqlite_size_mb:.2f} MB")
    print(f"   -> Tiết kiệm không gian đĩa         : {((sqlite_size_mb - duck_size_mb)/sqlite_size_mb)*100:.1f}%")

    # 4. TRUY VẤN ĐỐI CHUẨN (DUCKDB 1-THREAD vs DUCKDB 4-THREADS vs SQLITE 1-THREAD)
    print("\n[*] 4/4: Thực thi bộ 5 truy vấn phân tích (DuckDB 1T, DuckDB 4T vs SQLite 1T)...")
    
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
            "name": "Q4: P99 Latency Math (Phân vị độ trễ P99)",
            "duck_sql": "SELECT QUANTILE_CONT(latency_ms, 0.99) FROM edge_logs;",
            "sqlite_sql": "SELECT latency_ms FROM edge_logs ORDER BY latency_ms LIMIT 1 OFFSET (SELECT CAST(COUNT(*)*0.99 AS INT) FROM edge_logs);"
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
        # A. DuckDB 1-Thread (Đơn luồng công bằng đối chuẩn với SQLite)
        duck.conn.execute("SET threads = 1;")
        t_cold_duck_1t = time.perf_counter()
        duck.conn.execute(qdata["duck_sql"]).fetchall()
        cold_duck_1t = (time.perf_counter() - t_cold_duck_1t) * 1000.0

        duck_1t_times = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            duck.conn.execute(qdata["duck_sql"]).fetchall()
            duck_1t_times.append((time.perf_counter() - t0) * 1000.0)
        avg_duck_1t = sum(duck_1t_times) / len(duck_1t_times)

        # B. DuckDB 4-Threads (Đa luồng tối ưu phần cứng đa nhân)
        duck.conn.execute("SET threads = 4;")
        t_cold_duck_4t = time.perf_counter()
        duck.conn.execute(qdata["duck_sql"]).fetchall()
        cold_duck_4t = (time.perf_counter() - t_cold_duck_4t) * 1000.0

        duck_4t_times = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            duck.conn.execute(qdata["duck_sql"]).fetchall()
            duck_4t_times.append((time.perf_counter() - t0) * 1000.0)
        avg_duck_4t = sum(duck_4t_times) / len(duck_4t_times)

        # C. SQLite 1-Thread (Single-threaded B-Tree engine)
        t_cold_sqlite = time.perf_counter()
        sqlite.execute_query(qdata["sqlite_sql"])
        cold_sqlite = (time.perf_counter() - t_cold_sqlite) * 1000.0

        sqlite_times = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            sqlite.execute_query(qdata["sqlite_sql"])
            sqlite_times.append((time.perf_counter() - t0) * 1000.0)
        avg_sqlite = sum(sqlite_times) / len(sqlite_times)

        speedup_1t = avg_sqlite / max(avg_duck_1t, 0.001)
        speedup_4t = avg_sqlite / max(avg_duck_4t, 0.001)

        query_results[qkey] = {
            "name": qdata["name"],
            "duckdb_ms": round(avg_duck_4t, 2),
            "duckdb_1t_ms": round(avg_duck_1t, 2),
            "duckdb_4t_ms": round(avg_duck_4t, 2),
            "sqlite_ms": round(avg_sqlite, 2),
            "speedup": round(speedup_4t, 1),
            "speedup_1t": round(speedup_1t, 1),
            "speedup_4t": round(speedup_4t, 1),
            "cold_run_ms": {
                "duckdb_1t": round(cold_duck_1t, 2),
                "duckdb_4t": round(cold_duck_4t, 2),
                "sqlite": round(cold_sqlite, 2)
            }
        }
        print(f"   • {qdata['name']}")
        print(f"     DuckDB (1T): {avg_duck_1t:.2f} ms | DuckDB (4T): {avg_duck_4t:.2f} ms | SQLite (1T): {avg_sqlite:.2f} ms")
        print(f"     Speedup 1T (Vectorized): {speedup_1t:.1f}x | Speedup 4T (Parallel): {speedup_4t:.1f}x")

    results = {
        "total_rows": total_rows,
        "timestamp": datetime.datetime.now().isoformat(),
        "benchmark_metadata": {
            "evaluation_context": "In-situ Edge Sliding Window Evaluation (Hot Working Set)",
            "duckdb_threads": [1, 4],
            "sqlite_indexing": "Enabled (idx_logs_latency, idx_logs_level, idx_logs_ts)",
            "ingestion_method": "Pre-generated batches (Excludes Python data gen overhead)"
        },
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
