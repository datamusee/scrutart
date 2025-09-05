# WikimediaManagerPackage/metrics.py
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict, deque


@dataclass
class OperationMetrics:
    """Métriques pour une opération spécifique"""
    name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_types: Dict[str, int] = field(default_factory=dict)
    last_error: str = ""
    last_success: float = 0

    def record_success(self, response_time: float):
        self.total_calls += 1
        self.successful_calls += 1
        self.response_times.append(response_time)
        self.last_success = time.time()

    def record_error(self, error_type: str, response_time: float = 0):
        self.total_calls += 1
        self.failed_calls += 1
        if response_time > 0:
            self.response_times.append(response_time)
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        self.last_error = error_type

    def get_success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    def get_avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


class WikimediaMetricsCollector:
    """Collecteur de métriques pour WikimediaAccess"""

    def __init__(self):
        self.operations: Dict[str, OperationMetrics] = {}
        self.lock = threading.Lock()
        self.start_time = time.time()

    def record_operation_success(self, operation_name: str, response_time: float):
        with self.lock:
            if operation_name not in self.operations:
                self.operations[operation_name] = OperationMetrics(operation_name)
            self.operations[operation_name].record_success(response_time)

    def record_operation_error(self, operation_name: str, error_type: str, response_time: float = 0):
        with self.lock:
            if operation_name not in self.operations:
                self.operations[operation_name] = OperationMetrics(operation_name)
            self.operations[operation_name].record_error(error_type, response_time)

    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            metrics = {
                'uptime_seconds': time.time() - self.start_time,
                'operations': {}
            }

            total_calls = 0
            total_successes = 0

            for op_name, op_metrics in self.operations.items():
                metrics['operations'][op_name] = {
                    'total_calls': op_metrics.total_calls,
                    'successful_calls': op_metrics.successful_calls,
                    'failed_calls': op_metrics.failed_calls,
                    'success_rate_percent': op_metrics.get_success_rate(),
                    'avg_response_time_ms': op_metrics.get_avg_response_time() * 1000,
                    'error_types': dict(op_metrics.error_types),
                    'last_error': op_metrics.last_error
                }

                total_calls += op_metrics.total_calls
                total_successes += op_metrics.successful_calls

            # Métriques globales
            metrics['global'] = {
                'total_calls': total_calls,
                'total_successes': total_successes,
                'global_success_rate': (total_successes / max(total_calls, 1)) * 100
            }

            return metrics


# Instance globale pour collecter les métriques
metrics_collector = WikimediaMetricsCollector()
