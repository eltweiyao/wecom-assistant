"""
性能监控和健康检查模块
提供系统性能指标收集、健康状态检查和性能报告功能
"""
import time
import psutil
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

from logging_config import logger


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: str  # "healthy", "warning", "unhealthy"
    message: str
    timestamp: datetime
    response_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf')
        }
        self.active_requests = 0
        self.start_time = datetime.now()
        self._lock = threading.Lock()
        
        # 开始系统监控
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self._monitor_thread.start()
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录性能指标"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=name,
            value=value,
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics[name].append(metric)
        
        logger.debug(f"Recorded metric: {name}={value}", **tags or {})
    
    def record_request(self, success: bool, response_time: float):
        """记录请求统计"""
        with self._lock:
            self.request_stats["total_requests"] += 1
            if success:
                self.request_stats["successful_requests"] += 1
            else:
                self.request_stats["failed_requests"] += 1
            
            # 更新响应时间统计
            total_time = (self.request_stats["avg_response_time"] * 
                         (self.request_stats["total_requests"] - 1) + response_time)
            self.request_stats["avg_response_time"] = total_time / self.request_stats["total_requests"]
            
            if response_time > self.request_stats["max_response_time"]:
                self.request_stats["max_response_time"] = response_time
            if response_time < self.request_stats["min_response_time"]:
                self.request_stats["min_response_time"] = response_time
        
        self.record_metric("request_response_time", response_time, {"success": str(success)})
    
    def increment_active_requests(self):
        """增加活跃请求计数"""
        with self._lock:
            self.active_requests += 1
        self.record_metric("active_requests", self.active_requests)
    
    def decrement_active_requests(self):
        """减少活跃请求计数"""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
        self.record_metric("active_requests", self.active_requests)
    
    def get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计信息"""
        with self._lock:
            stats = self.request_stats.copy()
            stats["active_requests"] = self.active_requests
            stats["uptime"] = (datetime.now() - self.start_time).total_seconds()
            
            # 计算成功率
            if stats["total_requests"] > 0:
                stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
            else:
                stats["success_rate"] = 0
            
            return stats
    
    def get_metrics_summary(self, metric_name: str, hours: int = 1) -> Dict[str, float]:
        """获取指标摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            if metric_name not in self.metrics:
                return {}
            
            recent_metrics = [
                m for m in self.metrics[metric_name] 
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }
    
    def _collect_system_metrics(self):
        """后台收集系统指标"""
        while self._monitoring:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("system_cpu_percent", cpu_percent)
                
                # 内存使用率
                memory = psutil.virtual_memory()
                self.record_metric("system_memory_percent", memory.percent)
                self.record_metric("system_memory_used_mb", memory.used / 1024 / 1024)
                
                # 磁盘使用率
                disk = psutil.disk_usage('/')
                self.record_metric("system_disk_percent", disk.percent)
                
                time.sleep(30)  # 每30秒收集一次
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                time.sleep(60)  # 出错时延长间隔
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def register_check(self, name: str, check_func: callable):
        """注册健康检查"""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def run_check(self, name: str) -> HealthCheckResult:
        """运行单个健康检查"""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status="unhealthy",
                message=f"Unknown health check: {name}",
                timestamp=datetime.now()
            )
        
        start_time = time.time()
        try:
            result = self.checks[name]()
            response_time = time.time() - start_time
            
            if isinstance(result, HealthCheckResult):
                result.response_time = response_time
                self.last_results[name] = result
                return result
            else:
                # 如果返回值不是HealthCheckResult，认为是成功的
                result = HealthCheckResult(
                    name=name,
                    status="healthy",
                    message=str(result) if result else "OK",
                    timestamp=datetime.now(),
                    response_time=response_time
                )
                self.last_results[name] = result
                return result
                
        except Exception as e:
            response_time = time.time() - start_time
            result = HealthCheckResult(
                name=name,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time=response_time
            )
            self.last_results[name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """运行所有健康检查"""
        results = {}
        for name in self.checks:
            results[name] = self.run_check(name)
        return results
    
    def get_overall_status(self) -> str:
        """获取整体健康状态"""
        if not self.last_results:
            return "unknown"
        
        statuses = [result.status for result in self.last_results.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"


# 全局监控实例
performance_monitor = PerformanceMonitor()
health_checker = HealthChecker()


# 默认健康检查
def system_health_check() -> HealthCheckResult:
    """系统资源健康检查"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        status = "healthy"
        messages = []
        
        if cpu_percent > 80:
            status = "warning" if status == "healthy" else "unhealthy"
            messages.append(f"High CPU usage: {cpu_percent:.1f}%")
        
        if memory.percent > 80:
            status = "warning" if status == "healthy" else "unhealthy"
            messages.append(f"High memory usage: {memory.percent:.1f}%")
        
        if disk.percent > 90:
            status = "warning" if status == "healthy" else "unhealthy"
            messages.append(f"High disk usage: {disk.percent:.1f}%")
        
        return HealthCheckResult(
            name="system_resources",
            status=status,
            message="; ".join(messages) if messages else "System resources OK",
            timestamp=datetime.now(),
            details={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            }
        )
    except Exception as e:
        return HealthCheckResult(
            name="system_resources",
            status="unhealthy",
            message=f"Failed to check system resources: {str(e)}",
            timestamp=datetime.now()
        )


def request_rate_health_check() -> HealthCheckResult:
    """请求频率健康检查"""
    stats = performance_monitor.get_request_stats()
    
    status = "healthy"
    messages = []
    
    if stats["success_rate"] < 0.9 and stats["total_requests"] > 10:
        status = "warning"
        messages.append(f"Low success rate: {stats['success_rate']:.2%}")
    
    if stats["active_requests"] > 50:
        status = "warning" if status == "healthy" else "unhealthy"
        messages.append(f"High active requests: {stats['active_requests']}")
    
    if stats["avg_response_time"] > 10:
        status = "warning" if status == "healthy" else "unhealthy"
        messages.append(f"High avg response time: {stats['avg_response_time']:.2f}s")
    
    return HealthCheckResult(
        name="request_rate",
        status=status,
        message="; ".join(messages) if messages else "Request metrics OK",
        timestamp=datetime.now(),
        details=stats
    )


# 注册默认健康检查
health_checker.register_check("system_resources", system_health_check)
health_checker.register_check("request_rate", request_rate_health_check)


def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    return {
        "timestamp": datetime.now().isoformat(),
        "request_stats": performance_monitor.get_request_stats(),
        "system_metrics": {
            "cpu": performance_monitor.get_metrics_summary("system_cpu_percent"),
            "memory": performance_monitor.get_metrics_summary("system_memory_percent"),
            "disk": performance_monitor.get_metrics_summary("system_disk_percent"),
        },
        "health_status": health_checker.get_overall_status(),
        "health_checks": {
            name: {
                "status": result.status,
                "message": result.message,
                "timestamp": result.timestamp.isoformat(),
                "response_time": result.response_time
            }
            for name, result in health_checker.last_results.items()
        }
    }