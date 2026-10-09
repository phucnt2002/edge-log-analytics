import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import time
import json
import psutil
import datetime
import pyarrow as pa
from typing import Dict, Any

CLIENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CLIENT_DIR not in sys.path:
    sys.path.insert(0, CLIENT_DIR)

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

    data_dir = os.path.join(CLIENT_DIR, "data", "benchmark")
    os.makedirs(data_dir, exist_ok=True)
    node_id = os.getenv("NODE_ID", "")
    duck_name = f"bench_{node_id}.duckdb" if node_id else "bench.duckdb"
    sqlite_name = f"bench_{node_id}.sqlite" if node_id else "bench.sqlite"
    duck_path = os.path.join(data_dir, duck_name)
    sqlite_path = os.path.join(data_dir, sqlite_name)

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
            (str(r["timestamp"]), r["client_ip"], r["method"], r["endpoint"],
             r["status_code"], r["bytes_sent"], r.get("latency_ms", 0.0), r["label"], r["attack_type"], r.get("referer", "-"))
            for r in batch
        ]

        # B. Bấm giờ NẠP THUẦN TÚY vào DuckDB
        t0 = time.perf_counter()
        duck.insert_arrow_batch(tbl)
        t_duck_ingest += time.perf_counter() - t0

        # C. Bấm giờ NẠP THUẦN TÚY vào SQLite
        t0 = time.perf_counter()
        with sqlite.conn:
            sqlite.conn.executemany("INSERT INTO edge_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", tuples)
        t_sqlite_ingest += time.perf_counter() - t0

        # Giải phóng rác RAM ngay trong vòng lặp
        del batch, tbl, tuples

    duck_ingest_rate = total_rows / max(t_duck_ingest, 0.001)
    sqlite_ingest_rate = total_rows / max(t_sqlite_ingest, 0.001)
    print(f"   -> DuckDB Ingestion: {duck_ingest_rate:,.0f} rows/s (Thời gian nạp thuần: {t_duck_ingest:.2f}s)")
    print(f"   -> SQLite Ingestion: {sqlite_ingest_rate:,.0f} rows/s (Thời gian nạp thuần: {t_sqlite_ingest:.2f}s)")

    # Tạo Index tối ưu cho SQLite để đảm bảo cạnh tranh công bằng
    print("   -> Đang tạo Index tối ưu trên SQLite (idx_logs_label, idx_logs_status, idx_logs_bytes)...")
    sqlite.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_label ON edge_logs(label);")
    sqlite.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_status ON edge_logs(status_code);")
    sqlite.conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_bytes ON edge_logs(bytes_sent);")
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
    print("\n[*] 4/4: Thực thi bộ 5 truy vấn phân tích An ninh mạng (DuckDB 1T, DuckDB 4T vs SQLite 1T)...")
    
    queries = {
        "Q1_Count_Filter": {
            "name": "Q1: Attack Detection & Count (Đếm log tấn công)",
            "duck_sql": "SELECT COUNT(*) FROM edge_logs WHERE label = 'attack';",
            "sqlite_sql": "SELECT COUNT(*) FROM edge_logs WHERE label = 'attack';"
        },
        "Q2_Group_By": {
            "name": "Q2: Multi-dim Group By (Thống kê theo IP & Loại tấn công)",
            "duck_sql": "SELECT client_ip, attack_type, COUNT(*), AVG(bytes_sent) FROM edge_logs WHERE label = 'attack' GROUP BY client_ip, attack_type;",
            "sqlite_sql": "SELECT client_ip, attack_type, COUNT(*), AVG(bytes_sent) FROM edge_logs WHERE label = 'attack' GROUP BY client_ip, attack_type;"
        },
        "Q3_Window_Metrics": {
            "name": "Q3: Heavy Multi-Agg (Tổng hợp tải lỗi Server 5xx)",
            "duck_sql": """
                SELECT COUNT(*), AVG(bytes_sent), MAX(bytes_sent), MIN(bytes_sent)
                FROM edge_logs
                WHERE status_code >= 500;
            """,
            "sqlite_sql": """
                SELECT COUNT(*), AVG(bytes_sent), MAX(bytes_sent), MIN(bytes_sent)
                FROM edge_logs
                WHERE status_code >= 500;
            """
        },
        "Q4_Percentile_Math": {
            "name": "Q4: P99 Response Size Math (Phân vị dung lượng P99)",
            "duck_sql": "SELECT QUANTILE_CONT(bytes_sent, 0.99) FROM edge_logs;",
            "sqlite_sql": "SELECT bytes_sent FROM edge_logs ORDER BY bytes_sent LIMIT 1 OFFSET (SELECT CAST(COUNT(*)*0.99 AS INT) FROM edge_logs);"
        },
        "Q5_Pattern_Match": {
            "name": "Q5: Text Pattern Search (Quét payload tiêm SQL/Admin trong URL)",
            "duck_sql": "SELECT COUNT(*) FROM edge_logs WHERE endpoint LIKE '%union%' OR endpoint LIKE '%select%' OR endpoint LIKE '%admin%';",
            "sqlite_sql": "SELECT COUNT(*) FROM edge_logs WHERE endpoint LIKE '%union%' OR endpoint LIKE '%select%' OR endpoint LIKE '%admin%';"
        },
        "Q6_Global_Aggregation": {
            "name": "Q6: Global Fleet Aggregation (Gom nhóm tổng hợp toàn diện 100% logs)",
            "duck_sql": "SELECT method, COUNT(*), ROUND(AVG(latency_ms), 2), SUM(bytes_sent) FROM edge_logs GROUP BY method;",
            "sqlite_sql": "SELECT method, COUNT(*), ROUND(AVG(latency_ms), 2), SUM(bytes_sent) FROM edge_logs GROUP BY method;"
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

    # 5. ĐỐI CHUẨN ĐỒNG BỘ VÒNG ĐỜI DỮ LIỆU EDGE-TO-CLOUD (ROLLUP PARQUET EXPORT)
    print("\n[*] 5/5: Đo lường tốc độ Rollup và nén Parquet gửi lên Cloud (Edge-to-Cloud Sync)...")
    duck_rollup_path = os.path.join(data_dir, "duck_rollup_bench.parquet")
    sqlite_rollup_path = os.path.join(data_dir, "sqlite_rollup_bench.parquet")

    # DuckDB Native Rollup (Zero-copy C++)
    t0 = time.perf_counter()
    duck.export_parquet_rollup(duck_rollup_path, interval_minutes=15)
    t_duck_rollup = (time.perf_counter() - t0) * 1000.0
    duck_rollup_size_kb = os.path.getsize(duck_rollup_path) / 1024.0

    # SQLite Pipeline Rollup (Query -> Python Memory -> PyArrow -> Parquet)
    t0 = time.perf_counter()
    sqlite.export_parquet_rollup(sqlite_rollup_path, interval_minutes=15)
    t_sqlite_rollup = (time.perf_counter() - t0) * 1000.0
    sqlite_rollup_size_kb = os.path.getsize(sqlite_rollup_path) / 1024.0

    rollup_speedup = t_sqlite_rollup / max(t_duck_rollup, 0.001)
    print(f"   -> DuckDB Native C++ Rollup: {t_duck_rollup:.2f} ms | File: {duck_rollup_size_kb:.1f} KB (kèm hàm P99)")
    print(f"   -> SQLite Python Rollup    : {t_sqlite_rollup:.2f} ms | File: {sqlite_rollup_size_kb:.1f} KB (không hàm P99)")
    print(f"   -> DuckDB Rollup nhanh hơn : {rollup_speedup:.1f}x")

    for p in [duck_rollup_path, sqlite_rollup_path]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    process = psutil.Process()
    peak_ram_mb = process.memory_info().rss / (1024.0 * 1024.0)

    results = {
        "total_rows": total_rows,
        "timestamp": datetime.datetime.now().isoformat(),
        "benchmark_metadata": {
            "evaluation_context": "In-situ Edge Sliding Window Evaluation (Hot Working Set)",
            "duckdb_threads": [1, 4],
            "sqlite_indexing": "Enabled (idx_logs_latency, idx_logs_level, idx_logs_ts)",
            "ingestion_method": "Pre-generated batches (Excludes Python data gen overhead)",
            "peak_ram_mb": round(peak_ram_mb, 2)
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
        "edge_to_cloud_sync": {
            "duckdb_rollup_ms": round(t_duck_rollup, 2),
            "sqlite_rollup_ms": round(t_sqlite_rollup, 2),
            "speedup": round(rollup_speedup, 1),
            "duckdb_parquet_kb": round(duck_rollup_size_kb, 1),
            "sqlite_parquet_kb": round(sqlite_rollup_size_kb, 1)
        },
        "queries": query_results
    }

    result_json_path = os.path.join(CLIENT_DIR, "data", "benchmark_results.json")
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
