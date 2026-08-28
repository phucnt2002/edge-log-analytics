import asyncio
import datetime
from typing import Dict, Any, Callable
from core.duckdb_engine import DuckDBEngine
from core.alert_manager import AlertManager

class StreamAnalyzer:
    def __init__(self, duck_engine: DuckDBEngine, alert_mgr: AlertManager, window_seconds: int = 60, interval_seconds: int = 1):
        self.duck = duck_engine
        self.alert_mgr = alert_mgr
        self.window_seconds = window_seconds
        self.interval_seconds = interval_seconds
        
        self.is_running = False
        self.latest_metrics: Dict[str, Any] = {}
        self._task: asyncio.Task = None
        self.metric_listeners = []

    def add_metric_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.metric_listeners.append(callback)

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._analysis_loop())

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()

    async def _analysis_loop(self):
        while self.is_running:
            try:
                metrics = self.duck.get_sliding_window_metrics(self.window_seconds)
                metrics["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")
                metrics["total_stored_records"] = self.duck.get_total_count()
                self.latest_metrics = metrics
                
                self.alert_mgr.evaluate(metrics)

                for listener in self.metric_listeners:
                    try:
                        listener(metrics)
                    except Exception:
                        pass

                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[StreamAnalyzer] Lỗi phân tích: {e}")
                await asyncio.sleep(1)
