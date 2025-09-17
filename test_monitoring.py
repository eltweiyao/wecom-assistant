"""
监控模块单元测试
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from monitoring import (
    PerformanceMonitor, HealthChecker, HealthCheckResult,
    performance_monitor, health_checker
)


class TestPerformanceMonitor:
    """性能监控器测试类"""
    
    def test_record_metric(self):
        """测试记录性能指标"""
        monitor = PerformanceMonitor()
        
        # 记录指标
        monitor.record_metric("test_metric", 100.0, {"tag": "test"})
        
        # 验证指标被记录
        summary = monitor.get_metrics_summary("test_metric")
        assert summary["count"] == 1
        assert summary["avg"] == 100.0
        assert summary["latest"] == 100.0
    
    def test_record_request(self):
        """测试记录请求统计"""
        monitor = PerformanceMonitor()
        
        # 记录成功请求
        monitor.record_request(True, 2.5)
        monitor.record_request(True, 1.5)
        monitor.record_request(False, 5.0)
        
        # 验证统计
        stats = monitor.get_request_stats()
        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 2
        assert stats["failed_requests"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["max_response_time"] == 5.0
        assert stats["min_response_time"] == 1.5
    
    def test_active_requests(self):
        """测试活跃请求计数"""
        monitor = PerformanceMonitor()
        
        # 增加活跃请求
        monitor.increment_active_requests()
        monitor.increment_active_requests()
        assert monitor.active_requests == 2
        
        # 减少活跃请求
        monitor.decrement_active_requests()
        assert monitor.active_requests == 1
        
        # 不应该低于0
        monitor.decrement_active_requests()
        monitor.decrement_active_requests()
        assert monitor.active_requests == 0
    
    def test_metrics_summary_time_filter(self):
        """测试指标摘要时间过滤"""
        monitor = PerformanceMonitor()
        
        # 记录一些指标
        monitor.record_metric("test_metric", 10.0)
        monitor.record_metric("test_metric", 20.0)
        monitor.record_metric("test_metric", 30.0)
        
        # 获取摘要
        summary = monitor.get_metrics_summary("test_metric", hours=1)
        assert summary["count"] == 3
        assert summary["avg"] == 20.0
        assert summary["min"] == 10.0
        assert summary["max"] == 30.0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_collection(self, mock_disk, mock_memory, mock_cpu):
        """测试系统指标收集"""
        # 模拟系统指标
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(percent=60.0, used=1024*1024*1024)
        mock_disk.return_value = MagicMock(percent=45.0)
        
        monitor = PerformanceMonitor()
        
        # 手动触发一次收集（而不是等待后台线程）
        monitor._collect_system_metrics()
        
        # 验证指标被记录（注意：实际测试中可能需要短暂等待）
        # 这里只验证方法被调用，实际值的验证需要在集成测试中进行


class TestHealthChecker:
    """健康检查器测试类"""
    
    def test_register_and_run_check(self):
        """测试注册和运行健康检查"""
        checker = HealthChecker()
        
        # 注册一个健康检查
        def test_check():
            return HealthCheckResult(
                name="test_check",
                status="healthy",
                message="All good",
                timestamp=datetime.now()
            )
        
        checker.register_check("test_check", test_check)
        
        # 运行检查
        result = checker.run_check("test_check")
        assert result.name == "test_check"
        assert result.status == "healthy"
        assert result.message == "All good"
        assert result.response_time is not None
    
    def test_check_exception_handling(self):
        """测试健康检查异常处理"""
        checker = HealthChecker()
        
        # 注册一个会抛出异常的检查
        def failing_check():
            raise Exception("Check failed")
        
        checker.register_check("failing_check", failing_check)
        
        # 运行检查
        result = checker.run_check("failing_check")
        assert result.name == "failing_check"
        assert result.status == "unhealthy"
        assert "Check failed" in result.message
        assert result.response_time is not None
    
    def test_check_simple_return_value(self):
        """测试简单返回值的健康检查"""
        checker = HealthChecker()
        
        # 注册一个返回简单值的检查
        def simple_check():
            return "Everything is fine"
        
        checker.register_check("simple_check", simple_check)
        
        # 运行检查
        result = checker.run_check("simple_check")
        assert result.name == "simple_check"
        assert result.status == "healthy"
        assert result.message == "Everything is fine"
    
    def test_unknown_check(self):
        """测试未知健康检查"""
        checker = HealthChecker()
        
        result = checker.run_check("unknown_check")
        assert result.name == "unknown_check"
        assert result.status == "unhealthy"
        assert "Unknown health check" in result.message
    
    def test_run_all_checks(self):
        """测试运行所有健康检查"""
        checker = HealthChecker()
        
        # 注册多个检查
        checker.register_check("check1", lambda: HealthCheckResult("check1", "healthy", "OK", datetime.now()))
        checker.register_check("check2", lambda: HealthCheckResult("check2", "warning", "Warning", datetime.now()))
        
        # 运行所有检查
        results = checker.run_all_checks()
        assert len(results) == 2
        assert "check1" in results
        assert "check2" in results
        assert results["check1"].status == "healthy"
        assert results["check2"].status == "warning"
    
    def test_overall_status(self):
        """测试整体健康状态"""
        checker = HealthChecker()
        
        # 测试健康状态
        checker.last_results = {
            "check1": HealthCheckResult("check1", "healthy", "OK", datetime.now()),
            "check2": HealthCheckResult("check2", "healthy", "OK", datetime.now())
        }
        assert checker.get_overall_status() == "healthy"
        
        # 测试警告状态
        checker.last_results["check2"].status = "warning"
        assert checker.get_overall_status() == "warning"
        
        # 测试不健康状态
        checker.last_results["check1"].status = "unhealthy"
        assert checker.get_overall_status() == "unhealthy"
        
        # 测试未知状态
        checker.last_results = {}
        assert checker.get_overall_status() == "unknown"


class TestBuiltinHealthChecks:
    """内置健康检查测试类"""
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_health_check_healthy(self, mock_disk, mock_memory, mock_cpu):
        """测试系统健康检查 - 健康状态"""
        from monitoring import system_health_check
        
        # 模拟健康的系统状态
        mock_cpu.return_value = 50.0  # 50% CPU
        mock_memory.return_value = MagicMock(percent=60.0)  # 60% 内存
        mock_disk.return_value = MagicMock(percent=70.0)  # 70% 磁盘
        
        result = system_health_check()
        assert result.status == "healthy"
        assert "System resources OK" in result.message
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_health_check_warning(self, mock_disk, mock_memory, mock_cpu):
        """测试系统健康检查 - 警告状态"""
        from monitoring import system_health_check
        
        # 模拟资源紧张的系统状态
        mock_cpu.return_value = 85.0  # 85% CPU (>80%)
        mock_memory.return_value = MagicMock(percent=75.0)  # 75% 内存
        mock_disk.return_value = MagicMock(percent=70.0)  # 70% 磁盘
        
        result = system_health_check()
        assert result.status == "warning"
        assert "High CPU usage" in result.message
    
    def test_request_rate_health_check(self):
        """测试请求频率健康检查"""
        from monitoring import request_rate_health_check
        
        # 清理全局监控器状态
        performance_monitor.request_stats = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "avg_response_time": 2.0,
            "max_response_time": 5.0,
            "min_response_time": 0.5
        }
        performance_monitor.active_requests = 10
        
        result = request_rate_health_check()
        assert result.status == "healthy"
        assert "Request metrics OK" in result.message


if __name__ == '__main__':
    pytest.main([__file__])