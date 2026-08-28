import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import os
import json
import matplotlib.pyplot as plt
import numpy as np

def generate_charts(json_path: str = "data/benchmark_results.json", output_img: str = "data/benchmark_results.png"):
    if not os.path.exists(json_path):
        print(f"File {json_path} không tồn tại.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"ĐỐI CHUẨN HIỆU NĂNG CSDL NHÚNG TẠI BIÊN (EDGE COMPUTING)\nDuckDB (Columnar OLAP) vs SQLite (Row-oriented OLTP) - {data['total_rows']:,} Logs", 
                 fontsize=14, fontweight='bold', y=0.98)

    ax1 = axes[0, 0]
    q_names = [q['name'].split(':')[0] for q in data['queries'].values()]
    duck_latencies = [q['duckdb_ms'] for q in data['queries'].values()]
    sqlite_latencies = [q['sqlite_ms'] for q in data['queries'].values()]

    x = np.arange(len(q_names))
    width = 0.35

    rects1 = ax1.bar(x - width/2, duck_latencies, width, label='DuckDB (Vectorized)', color='#0284c7')
    rects2 = ax1.bar(x + width/2, sqlite_latencies, width, label='SQLite (B-Tree)', color='#dc2626')

    ax1.set_ylabel('Thời gian thực thi (ms) - Thấp hơn là tốt hơn', fontweight='bold')
    ax1.set_title('1. Độ Trễ Truy Vấn Phân Tích (Query Latency)', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(q_names, fontweight='bold')
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.6)

    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}ms', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, color='#0369a1')
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}ms', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, color='#b91c1c')

    ax2 = axes[0, 1]
    db_labels = ['DuckDB\n(Arrow Appender)', 'SQLite\n(WAL Executemany)']
    throughputs = [data['ingestion']['duckdb_rows_per_sec'], data['ingestion']['sqlite_rows_per_sec']]
    colors = ['#0284c7', '#dc2626']

    bars2 = ax2.bar(db_labels, throughputs, color=colors, width=0.45)
    ax2.set_ylabel('Throughput (Bản ghi / Giây) - Cao hơn là tốt hơn', fontweight='bold')
    ax2.set_title('2. Tốc Độ Nạp Dữ Liệu (Ingestion Rate)', fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.6)

    for bar in bars2:
        h = bar.get_height()
        ax2.annotate(f'{h:,.0f} rows/s', xy=(bar.get_x() + bar.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold')

    ax3 = axes[1, 0]
    sizes = [data['storage']['duckdb_size_mb'], data['storage']['sqlite_size_mb']]
    bars3 = ax3.bar(db_labels, sizes, color=colors, width=0.45)
    ax3.set_ylabel('Dung lượng File trên Đĩa (MB) - Nhỏ hơn là tốt hơn', fontweight='bold')
    ax3.set_title(f"3. Dung Lượng Đĩa & Tiết Kiệm Bộ Nhớ Flash (Tiết kiệm {data['storage']['space_saving_pct']}%)", fontweight='bold')
    ax3.grid(True, linestyle='--', alpha=0.6)

    for bar in bars3:
        h = bar.get_height()
        ax3.annotate(f'{h:.2f} MB', xy=(bar.get_x() + bar.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold')

    ax4 = axes[1, 1]
    speedups = [q['speedup'] for q in data['queries'].values()]
    y_pos = np.arange(len(q_names))
    
    ax4.barh(y_pos, speedups, color='#10b981', height=0.55)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(q_names, fontweight='bold')
    ax4.set_xlabel('Số lần DuckDB chạy nhanh hơn SQLite (Speedup Factor)', fontweight='bold')
    ax4.set_title('4. Tỷ Lệ Tăng Tốc Của DuckDB So Với SQLite', fontweight='bold')
    ax4.grid(True, linestyle='--', alpha=0.6)

    for i, v in enumerate(speedups):
        ax4.text(v + 0.5, i, f'{v:.1f}x Nhanh Hơn', va='center', fontweight='bold', color='#047857')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    os.makedirs(os.path.dirname(os.path.abspath(output_img)), exist_ok=True)
    plt.savefig(output_img, dpi=200)
    plt.close()
    print(f"[✓] Đã xuất biểu đồ so sánh chất lượng cao tại: {output_img}")

if __name__ == "__main__":
    generate_charts()
