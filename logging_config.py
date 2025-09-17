"""
结构化日志系统
提供统一的日志记录功能，支持不同级别的日志和结构化输出
"""
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import config


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON格式"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加额外的上下文信息
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'token_usage'):
            log_entry['token_usage'] = record.token_usage
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class WecomAssistantLogger:
    """企业微信助手专用日志器"""
    
    def __init__(self, name: str = "wecom_assistant"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / "wecom_assistant.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 错误文件处理器
        error_handler = logging.FileHandler(
            log_dir / "error.log",
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # 设置格式化器
        formatter = StructuredFormatter()
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def _log_with_extra(self, level: str, message: str, **kwargs):
        """带额外信息的日志记录"""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        getattr(self.logger, level)(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self._log_with_extra('info', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self._log_with_extra('debug', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self._log_with_extra('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self._log_with_extra('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        self._log_with_extra('critical', message, **kwargs)
    
    def log_request_start(self, user_id: str, message_type: str, request_id: str):
        """记录请求开始"""
        self.info(
            f"Processing message from user {user_id}",
            user_id=user_id,
            message_type=message_type,
            request_id=request_id,
            event="request_start"
        )
    
    def log_request_end(self, user_id: str, request_id: str, execution_time: float, success: bool = True):
        """记录请求结束"""
        level = "info" if success else "error"
        self._log_with_extra(
            level,
            f"Request completed for user {user_id}",
            user_id=user_id,
            request_id=request_id,
            execution_time=execution_time,
            success=success,
            event="request_end"
        )
    
    def log_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int, cost: float = None):
        """记录LLM调用"""
        self.info(
            f"LLM call completed",
            model=model,
            token_usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost": cost
            },
            event="llm_call"
        )
    
    def log_tool_call(self, tool_name: str, execution_time: float, success: bool, result_length: int = None):
        """记录工具调用"""
        level = "info" if success else "error"
        self._log_with_extra(
            level,
            f"Tool {tool_name} execution {'completed' if success else 'failed'}",
            tool_name=tool_name,
            execution_time=execution_time,
            success=success,
            result_length=result_length,
            event="tool_call"
        )
    
    def log_wecom_event(self, event_type: str, user_id: str, details: Dict[str, Any] = None):
        """记录企业微信事件"""
        self.info(
            f"WeChat event: {event_type}",
            user_id=user_id,
            event_type=event_type,
            details=details or {},
            event="wecom_event"
        )
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """记录性能指标"""
        self.info(
            "Performance metrics",
            **metrics,
            event="performance_metrics"
        )
    
    def log_exception(self, exception: Exception, context: str = "", **kwargs):
        """记录异常"""
        self.error(
            f"Exception in {context}: {str(exception)}",
            exception_type=type(exception).__name__,
            context=context,
            **kwargs,
            exc_info=True,
            event="exception"
        )


# 创建全局日志器实例
logger = WecomAssistantLogger()

# 便捷函数
def log_info(message: str, **kwargs):
    """便捷的信息日志函数"""
    logger.info(message, **kwargs)

def log_error(message: str, **kwargs):
    """便捷的错误日志函数"""
    logger.error(message, **kwargs)

def log_debug(message: str, **kwargs):
    """便捷的调试日志函数"""
    logger.debug(message, **kwargs)

def log_warning(message: str, **kwargs):
    """便捷的警告日志函数"""
    logger.warning(message, **kwargs)