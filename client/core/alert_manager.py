import json
import datetime
from typing import List, Dict, Any, Callable

class AlertManager:
    def __init__(self, rules_path: str = "config/rules.json"):
        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.recent_alerts: List[Dict[str, Any]] = []
        self.alert_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def _load_rules(self) -> List[Dict[str, Any]]:
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.alert_listeners.append(callback)

    def evaluate(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered_alerts = []
        now = datetime.datetime.now().strftime("%H:%M:%S")

        for rule in self.rules:
            cond = rule.get("condition", "")
            ctx = {
                "error_rate_pct": metrics.get("error_rate_pct", 0.0),
                "attack_rate_pct": metrics.get("attack_rate_pct", 0.0),
                "attack_count": metrics.get("attack_count", 0),
                "p99_latency_ms": metrics.get("p99_latency", 0.0),
                "p99_latency": metrics.get("p99_latency", 0.0),
                "p99_bytes": metrics.get("p99_bytes", 0.0),
                "avg_bytes": metrics.get("avg_bytes", 0.0),
                "avg_cpu_usage": metrics.get("avg_cpu", 0.0),
                "total_logs": metrics.get("total_logs", 0),
                "active_ips": metrics.get("active_ips", 0)
            }
            try:
                if ctx["total_logs"] > 0 and eval(cond, {}, ctx):
                    alert_event = {
                        "id": rule["id"],
                        "time": now,
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "trigger_val": ctx
                    }
                    triggered_alerts.append(alert_event)
                    self.recent_alerts.insert(0, alert_event)
                    if len(self.recent_alerts) > 50:
                        self.recent_alerts.pop()
                    
                    for listener in self.alert_listeners:
                        try:
                            listener(alert_event)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[AlertManager] Lỗi eval rule {rule['id']}: {e}")

        return triggered_alerts
