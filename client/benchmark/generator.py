import random
import datetime
import pyarrow as pa
from typing import List, Dict, Any

SERVICES = ["sensor-telemetry", "motor-controller", "thermal-scanner", "network-gateway", "power-monitor"]
LOG_LEVELS = ["INFO", "INFO", "INFO", "DEBUG", "WARN", "ERROR", "CRITICAL"]
LOG_WEIGHTS = [0.65, 0.15, 0.08, 0.05, 0.04, 0.02, 0.01]

ERROR_MESSAGES = [
    "Connection timeout to peripheral device.",
    "Voltage drop below 3.1V threshold detected.",
    "High temperature alert: Core reached 88C.",
    "Packet checksum mismatch, retrying frame transmit.",
    "Flash write buffer full, throttling ingestion.",
    "Failed to acquire mutex lock for SPI bus."
]

NORMAL_MESSAGES = [
    "Periodic heartbeat ok, battery status 98%.",
    "Sensor calibration completed successfully.",
    "Frame telemetry uploaded to local ring buffer.",
    "Readings synchronized with RTC clock.",
    "Sampling rate maintained at 100Hz stable."
]

def generate_log_batch(count: int, start_time: datetime.datetime, device_count: int = 50, anomaly_rate: float = 0.05) -> List[Dict[str, Any]]:
    records = []
    current_time = start_time
    time_step = datetime.timedelta(milliseconds=max(1, 1000 // max(count, 1)))

    for i in range(count):
        is_anomaly = random.random() < anomaly_rate
        device_id = f"dev-{random.randint(1, device_count):03d}"
        service = random.choice(SERVICES)
        
        if is_anomaly:
            level = random.choice(["ERROR", "CRITICAL"])
            cpu = round(random.uniform(85.0, 99.5), 2)
            mem = random.randint(10, 45)
            latency = round(random.uniform(1200.0, 3500.0), 2)
            status = random.choice([500, 503, 504])
            msg = random.choice(ERROR_MESSAGES)
        else:
            level = random.choices(LOG_LEVELS, weights=LOG_WEIGHTS)[0]
            cpu = round(random.uniform(15.0, 65.0), 2)
            mem = random.randint(120, 240)
            latency = round(random.uniform(5.0, 150.0), 2)
            status = 200
            msg = random.choice(NORMAL_MESSAGES)

        records.append({
            "timestamp": current_time,
            "device_id": device_id,
            "log_level": level,
            "service_name": service,
            "cpu_usage": cpu,
            "memory_free_mb": mem,
            "latency_ms": latency,
            "status_code": status,
            "message": msg
        })
        current_time += time_step

    return records
