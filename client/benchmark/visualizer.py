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
    duck_1t_lat = [q.get('duckdb_1t_ms', q['duckdb_ms']) for q in data['queries'].values()]
    duck_4t_lat = [q.get('duckdb_4t_ms', q['duckdb_ms']) for q in data['queries'].values()]
    sqlite_latencies = [q['sqlite_ms'] for q in data['queries'].values()]

    x = np.arange(len(q_names))
    width = 0.26

    rects1 = ax1.bar(x - width, duck_1t_lat, width, label='DuckDB (1T - Vectorized)', color='#38bdf8')
    rects2 = ax1.bar(x, duck_4t_lat, width, label='DuckDB (4T - Parallel)', color='#0284c7')
    rects3 = ax1.bar(x + width, sqlite_latencies, width, label='SQLite (1T - Indexed B-Tree)', color='#dc2626')

    ax1.set_ylabel('Thời gian thực thi (ms) - Thấp hơn là tốt hơn', fontweight='bold')
    ax1.set_title('1. Độ Trễ Truy Vấn Phân Tích (Query Latency: 1T vs 4T)', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(q_names, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.6)

    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, color='#0284c7', fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, color='#0369a1', fontweight='bold')
    for rect in rects3:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, color='#b91c1c', fontweight='bold')

    ax2 = axes[0, 1]
    db_labels = ['DuckDB\n(Arrow Appender)', 'SQLite\n(WAL Executemany)']
    throughputs = [data['ingestion']['duckdb_rows_per_sec'], data['ingestion']['sqlite_rows_per_sec']]
    colors = ['#0284c7', '#dc2626']

    bars2 = ax2.bar(db_labels, throughputs, color=colors, width=0.45)
    ax2.set_ylabel('Throughput (Bản ghi / Giây) - Cao hơn là tốt hơn', fontweight='bold')
    ax2.set_title('2. Tốc Độ Nạp Dữ Liệu Thuần Túy (Pure Ingestion Rate)', fontweight='bold')
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

    if 'edge_to_cloud_sync' in data:
        sync = data['edge_to_cloud_sync']
        ax3.set_xlabel(f"Rollup Parquet: DuckDB {sync['duckdb_rollup_ms']:.0f}ms vs SQLite {sync['sqlite_rollup_ms']:.0f}ms (DuckDB {sync['speedup']}x nhanh hơn)",
                       fontweight='bold', color='#0369a1', fontsize=9.5)

    ax4 = axes[1, 1]
    speedups_1t = [q.get('speedup_1t', q['speedup']) for q in data['queries'].values()]
    speedups_4t = [q.get('speedup_4t', q['speedup']) for q in data['queries'].values()]
    y_pos = np.arange(len(q_names))
    h_bar = 0.35
    
    b1 = ax4.barh(y_pos - h_bar/2, speedups_1t, h_bar, label='Speedup 1T (Thuần Vectorized)', color='#38bdf8')
    b2 = ax4.barh(y_pos + h_bar/2, speedups_4t, h_bar, label='Speedup 4T (Vectorized + Parallel)', color='#10b981')
    
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(q_names, fontweight='bold')
    ax4.set_xlabel('Hệ số tăng tốc so với SQLite (Speedup Factor)', fontweight='bold')
    ax4.set_title('4. Tỷ Lệ Tăng Tốc Của DuckDB So Với SQLite (1T vs 4T)', fontweight='bold')
    ax4.legend(fontsize=9, loc='lower right')
    ax4.grid(True, linestyle='--', alpha=0.6)

    for i, v in enumerate(speedups_1t):
        ax4.text(v + 0.2, i - h_bar/2, f'{v:.1f}x (1T)', va='center', fontsize=8, fontweight='bold', color='#0284c7')
    for i, v in enumerate(speedups_4t):
        ax4.text(v + 0.2, i + h_bar/2, f'{v:.1f}x (4T)', va='center', fontsize=8, fontweight='bold', color='#047857')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    os.makedirs(os.path.dirname(os.path.abspath(output_img)), exist_ok=True)
    plt.savefig(output_img, dpi=200)
    plt.close()
    print(f"[✓] Đã xuất biểu đồ so sánh chất lượng cao tại: {output_img}")

if __name__ == "__main__":
    generate_charts()
