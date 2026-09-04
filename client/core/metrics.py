import os
import psutil
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

NODE_ID = os.getenv("NODE_ID", "edge-gateway-01")

LOGS_PROCESSED = Counter(
    'edge_logs_processed_total',
    'Tổng số bản ghi log đã xử lý tại thiết bị biên',
    ['node_id']
)

ERROR_RATE = Gauge(
    'edge_error_rate_pct',
    'Tỷ lệ phần trăm log ERROR/CRITICAL trong cửa sổ trượt 60s',
    ['node_id']
)

P99_LATENCY = Gauge(
    'edge_p99_latency_ms',
    'Độ trễ phản hồi phân vị P99 (ms) tính toán tại biên',
    ['node_id']
)

MEMORY_USAGE = Gauge(
    'edge_memory_usage_bytes',
    'Dung lượng RAM (Bytes) tiến trình DuckDB đang chiếm dụng',
    ['node_id']
)

CPU_USAGE = Gauge(
    'edge_cpu_usage_pct',
    'Mức độ sử dụng CPU (%) của thiết bị biên',
    ['node_id']
)

BANDWIDTH_SAVED = Gauge(
    'edge_bandwidth_saved_pct',
    'Tỷ lệ phần trăm băng thông mạng tiết kiệm được nhờ nén Parquet',
    ['node_id']
)

ACTIVE_ALERTS = Gauge(
    'edge_active_alerts_count',
    'Số lượng cảnh báo sự cố nghiêm trọng đang kích hoạt',
    ['node_id']
)

def update_prometheus_metrics(metrics_dict: dict, alerts_count: int = 0):
    process = psutil.Process(os.getpid())
    ram_bytes = process.memory_info().rss
    cpu_pct = process.cpu_percent(interval=None)

    LOGS_PROCESSED.labels(node_id=NODE_ID).inc(metrics_dict.get("new_logs_count", 0))
    ERROR_RATE.labels(node_id=NODE_ID).set(metrics_dict.get("error_rate_pct", 0.0))
    P99_LATENCY.labels(node_id=NODE_ID).set(metrics_dict.get("p99_latency", 0.0))
    MEMORY_USAGE.labels(node_id=NODE_ID).set(ram_bytes)
    CPU_USAGE.labels(node_id=NODE_ID).set(cpu_pct or metrics_dict.get("avg_cpu", 0.0))
    BANDWIDTH_SAVED.labels(node_id=NODE_ID).set(metrics_dict.get("bandwidth_saved_pct", 0.0))
    ACTIVE_ALERTS.labels(node_id=NODE_ID).set(alerts_count)
