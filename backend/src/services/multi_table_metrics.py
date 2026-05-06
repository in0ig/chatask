"""
多表治理基础埋点（进程内计数）。
"""

from collections import defaultdict
from threading import Lock
from typing import DefaultDict, Dict


class MultiTableMetrics:
    def __init__(self) -> None:
        self._counters: DefaultDict[str, int] = defaultdict(int)
        self._lock = Lock()

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def get(self, name: str) -> int:
        with self._lock:
            return int(self._counters.get(name, 0))

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)


_METRICS = MultiTableMetrics()


def get_multi_table_metrics() -> MultiTableMetrics:
    return _METRICS
