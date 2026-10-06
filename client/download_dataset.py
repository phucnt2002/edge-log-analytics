import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
import argparse
import datetime
import pyarrow as pa
import pyarrow.csv as pacsv

from benchmark.generator import generate_log_batch

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def check_status():
    csv_file = os.path.join(DATA_DIR, "web_server_access_logs.csv")
    print("====================================================================")
    print("     TRẠNG THÁI TẬP DỮ LIỆU: WEB SERVER ACCESS LOGS - LABELED      ")
    print("====================================================================")
    if os.path.exists(csv_file):
        size_mb = os.path.getsize(csv_file) / (1024.0 * 1024.0)
        print(f"[✓] Đã tìm thấy file dataset: {csv_file} ({size_mb:.2f} MB)")
    else:
        print("[!] Chưa có file 'data/web_server_access_logs.csv'.")
        print("\n[*] Bạn có thể tải tập dữ liệu chính thức từ Kaggle theo 2 cách:")
        print("  Cách 1: Tải trực tiếp bằng trình duyệt tại URL:")
        print("          https://www.kaggle.com/datasets/mahendradata/web-server-access-logs-labeled")
        print("          Sau đó giải nén và đổi tên file CSV thành 'web_server_access_logs.csv'")
        print(f"          rồi đặt vào thư mục: {DATA_DIR}")
        print("\n  Cách 2: Sử dụng Kaggle API trong terminal:")
        print(f"          kaggle datasets download -d mahendradata/web-server-access-logs-labeled -p {DATA_DIR} --unzip")

def create_sample_csv(rows: int = 100000):
    os.makedirs(DATA_DIR, exist_ok=True)
    out_csv = os.path.join(DATA_DIR, "web_server_access_logs.csv")
    print(f"[*] Đang khởi tạo tập dữ liệu mẫu chuẩn Kaggle ({rows:,} dòng) tại: {out_csv} ...")
    
    batch_size = 10000
    start_time = datetime.datetime(2026, 9, 1, 8, 0, 0)
    
    all_batches = []
    for offset in range(0, rows, batch_size):
        batch = generate_log_batch(batch_size, start_time + datetime.timedelta(seconds=offset))
        all_batches.extend(batch)
    
    table = pa.Table.from_pylist(all_batches)
    pacsv.write_csv(table, out_csv)
    size_mb = os.path.getsize(out_csv) / (1024.0 * 1024.0)
    print(f"[✓] Đã tạo thành công file CSV ({size_mb:.2f} MB) với đúng 100% cấu trúc Web Access Logs Labeled!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quản lý tập dữ liệu Web Server Access Logs")
    parser.add_argument("--create-sample", type=int, default=0, help="Tạo file CSV mẫu (VD: --create-sample 100000)")
    args = parser.parse_args()

    if args.create_sample > 0:
        create_sample_csv(args.create_sample)
    else:
        check_status()
