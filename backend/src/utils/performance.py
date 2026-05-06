import time
import psutil
import os
from typing import Any, Callable, Dict, Optional
from functools import wraps

class PerformanceMetrics:
    """收集和报告性能指标"""
    
    def __init__(self):
        self.metrics = {}
    
    def add_metric(self, name: str, value: float, unit: str = "seconds"):
        """添加性能指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({"value": value, "unit": unit})
    
    def get_average(self, name: str) -> Optional[float]:
        """获取指标的平均值"""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return None
        return sum(m["value"] for m in self.metrics[name]) / len(self.metrics[name])
    
    def get_max(self, name: str) -> Optional[float]:
        """获取指标的最大值"""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return None
        return max(m["value"] for m in self.metrics[name])
    
    def get_min(self, name: str) -> Optional[float]:
        """获取指标的最小值"""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return None
        return min(m["value"] for m in self.metrics[name])
    
    def get_report(self) -> Dict[str, Dict[str, Any]]:
        """获取完整的性能报告"""
        report = {}
        for name, values in self.metrics.items():
            report[name] = {
                "count": len(values),
                "average": self.get_average(name),
                "min": self.get_min(name),
                "max": self.get_max(name),
                "unit": values[0]["unit"] if values else "unknown"
            }
        return report
    
    def clear(self):
        """清除所有指标"""
        self.metrics = {}

# 全局性能指标实例
performance_metrics = PerformanceMetrics()

def measure_time(func: Callable) -> Callable:
    """测量函数执行时间的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 记录性能指标
        performance_metrics.add_metric(f"{func.__name__}_time", execution_time)
        
        # 可选：打印执行时间（在测试中可关闭）
        # print(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper

def memory_profile(func: Callable) -> Callable:
    """测量函数内存使用的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 获取当前进程
        process = psutil.Process(os.getpid())
        
        # 记录开始时的内存使用
        memory_start = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 记录结束时的内存使用
        memory_end = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_end - memory_start
        
        # 记录性能指标
        performance_metrics.add_metric(f"{func.__name__}_memory", memory_used, "MB")
        
        # 可选：打印内存使用
        # print(f"{func.__name__} used {memory_used:.2f} MB of memory")
        
        return result
    return wrapper