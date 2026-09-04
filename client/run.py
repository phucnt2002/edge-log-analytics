import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import uvicorn
from benchmark.runner import run_benchmark
from benchmark.visualizer import generate_charts

def main():
    print("====================================================================")
    print("      EDGE LOG ANALYTICS ENGINE: DUCKDB vs SQLITE IN-SITU           ")
    print("====================================================================")
    
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    bench_json = os.path.join(data_dir, "benchmark_results.json")
    bench_img = os.path.join(data_dir, "benchmark_results.png")

    if not os.path.exists(bench_json) or not os.path.exists(bench_img) or os.path.getsize(bench_json) == 0:
        print("[*] Chưa tìm thấy dữ liệu benchmark mẫu. Đang chạy khởi tạo đối chuẩn 100,000 logs...")
        run_benchmark(total_rows=100000, batch_size=5000)
        generate_charts(json_path=bench_json, output_img=bench_img)

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n[*] Đang khởi chạy Local Web Server & WebSocket Hub tại: http://{host}:{port}")
    print("[*] Nhấn Ctrl+C để dừng hệ thống.\n")

    uvicorn.run("server.app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
