import sys
import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Fix PyCharm 2024 debugger bug with Python 3.12+ and Uvicorn (loop_factory error)
def _patch_pycharm_debugger():
    import asyncio
    try:
        orig_run = asyncio.run
        def safe_asyncio_run(main, *args, **kwargs):
            kwargs.pop("loop_factory", None)
            try:
                return orig_run(main, *args, **kwargs)
            except TypeError:
                return orig_run(main)
        asyncio.run = safe_asyncio_run
    except Exception:
        pass

    try:
        import uvicorn.server
        orig_uvicorn_run = uvicorn.server.asyncio_run
        def safe_uvicorn_run(main, *args, **kwargs):
            kwargs.pop("loop_factory", None)
            try:
                return orig_uvicorn_run(main, *args, **kwargs)
            except TypeError:
                return orig_uvicorn_run(main)
        uvicorn.server.asyncio_run = safe_uvicorn_run
    except Exception:
        pass

    try:
        import uvicorn._compat
        orig_compat_run = uvicorn._compat.asyncio_run
        def safe_compat_run(main, *args, **kwargs):
            kwargs.pop("loop_factory", None)
            try:
                return orig_compat_run(main, *args, **kwargs)
            except TypeError:
                return orig_compat_run(main)
        uvicorn._compat.asyncio_run = safe_compat_run
    except Exception:
        pass

_patch_pycharm_debugger()

from core.duckdb_engine import DuckDBEngine
from core.ingestion import IngestBuffer
from core.alert_manager import AlertManager
from core.analyzer import StreamAnalyzer
from core.cloud_syncer import CloudSyncer
from core.metrics import generate_latest, CONTENT_TYPE_LATEST, update_prometheus_metrics
from benchmark.generator import generate_log_batch
from benchmark.runner import run_benchmark
from benchmark.visualizer import generate_charts

STATIC_DIR = os.path.join(BASE_DIR, "ui", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "ui", "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")

node_id = os.getenv("NODE_ID", "")
db_filename = f"edge_logs_{node_id}.duckdb" if node_id else "edge_logs.duckdb"
duck_engine = DuckDBEngine(db_path=os.path.join(DATA_DIR, db_filename), max_memory_mb=256, threads=4)
ingest_buffer = IngestBuffer(duck_engine=duck_engine, batch_size=500, flush_interval_ms=500)
alert_manager = AlertManager(rules_path=os.path.join(BASE_DIR, "config", "rules.json"))
stream_analyzer = StreamAnalyzer(duck_engine=duck_engine, alert_mgr=alert_manager, window_seconds=60, interval_seconds=1)
cloud_syncer = CloudSyncer(duck_engine=duck_engine, export_dir=os.path.join(DATA_DIR, "parquet_rollups"))

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

def on_new_metric(metrics: dict):
    metrics["bandwidth_saved_pct"] = cloud_syncer.latest_bandwidth_saved_pct
    current_active_alerts = metrics.get("active_alerts_count", 0)
    update_prometheus_metrics(metrics, current_active_alerts)
    asyncio.create_task(manager.broadcast({"type": "metric_update", "data": metrics}))

def on_new_alert(alert: dict):
    asyncio.create_task(manager.broadcast({"type": "alert_event", "data": alert}))

stream_analyzer.add_metric_listener(on_new_metric)
alert_manager.add_listener(on_new_alert)

async def background_log_stream():
    import datetime
    while True:
        try:
            batch = generate_log_batch(count=150, start_time=datetime.datetime.now(), device_count=20, anomaly_rate=0.06)
            await ingest_buffer.push_batch(batch)
            metrics_dict = {
                "new_logs_count": len(batch),
                "bandwidth_saved_pct": cloud_syncer.latest_bandwidth_saved_pct
            }
            active_cnt = stream_analyzer.latest_metrics.get("active_alerts_count", 0)
            update_prometheus_metrics(metrics_dict, active_cnt)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Stream generator error: {e}")
            await asyncio.sleep(1)

async def background_rollup_sync():
    """Tự động xuất bản và gửi Parquet Rollup lên Cloud định kỳ để đo lường băng thông tiết kiệm"""
    await asyncio.sleep(4)  # Đợi DuckDB nạp lứa log ban đầu
    while True:
        try:
            if duck_engine.get_total_count() > 0:
                cloud_syncer.trigger_rollup_export(interval_minutes=15)
        except Exception as e:
            print(f"[CloudSyncer] Rollup sync error: {e}")
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ingest_buffer.start()
    await stream_analyzer.start()
    generator_task = asyncio.create_task(background_log_stream())
    rollup_task = asyncio.create_task(background_rollup_sync())
    yield
    generator_task.cancel()
    rollup_task.cancel()
    await stream_analyzer.stop()
    await ingest_buffer.stop()
    duck_engine.close()

app = FastAPI(title="Edge Log Analytics Engine", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/metrics")
async def get_prometheus_metrics():
    """Endpoint chuẩn Prometheus cào số liệu"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "initial_state",
            "metrics": stream_analyzer.latest_metrics,
            "recent_alerts": alert_manager.recent_alerts
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/trigger-rollup")
async def api_trigger_rollup():
    file_path = cloud_syncer.trigger_rollup_export(interval_minutes=5)
    return {"status": "success", "file": file_path, "size_kb": round(os.path.getsize(file_path)/1024.0, 1)}

@app.post("/api/run-benchmark")
async def api_run_benchmark(rows: int = 100000):
    results = run_benchmark(total_rows=rows)
    generate_charts(json_path="data/benchmark_results.json", output_img="data/benchmark_results.png")
    return {"status": "success", "data": results}

@app.get("/api/benchmark-results")
async def api_get_benchmark_results():
    json_path = os.path.join(DATA_DIR, "benchmark_results.json")
    if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"error": "Chưa chạy benchmark"}

@app.get("/api/benchmark-image")
async def api_get_benchmark_image():
    img_path = os.path.join(DATA_DIR, "benchmark_results.png")
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "Image not found"})

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print("====================================================================")
    print("      EDGE LOG ANALYTICS ENGINE: LOCAL SERVER RUNNER               ")
    print(f"[*] Đang khởi chạy máy chủ tại: http://{host}:{port}")
    print("====================================================================")
    uvicorn.run(app, host=host, port=port, log_level="info")

