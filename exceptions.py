"""
自定义异常类和错误处理器
提供统一的错误处理机制，便于错误追踪和用户友好的错误提示
"""
import traceback
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """错误代码枚举"""
    # 企业微信相关错误
    WECOM_SIGNATURE_INVALID = "WECOM_001"
    WECOM_MESSAGE_PARSE_ERROR = "WECOM_002"
    WECOM_API_ERROR = "WECOM_003"
    
    # LLM相关错误
    LLM_API_ERROR = "LLM_001"
    LLM_TIMEOUT = "LLM_002"
    LLM_QUOTA_EXCEEDED = "LLM_003"
    
    # 工具相关错误
    TOOL_EXECUTION_ERROR = "TOOL_001"
    MEDIA_DOWNLOAD_ERROR = "TOOL_002"
    FILE_PARSING_ERROR = "TOOL_003"
    
    # 系统错误
    CONFIG_ERROR = "SYS_001"
    NETWORK_ERROR = "SYS_002"
    UNKNOWN_ERROR = "SYS_999"


class WecomAssistantException(Exception):
    """基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.user_message = user_message or "抱歉，系统遇到了一些问题，请稍后再试。"
        self.traceback = traceback.format_exc()


class WecomException(WecomAssistantException):
    """企业微信相关异常"""
    pass


class LLMException(WecomAssistantException):
    """LLM相关异常"""
    pass


class ToolException(WecomAssistantException):
    """工具执行异常"""
    pass


class ConfigException(WecomAssistantException):
    """配置相关异常"""
    pass


def handle_exception(
    exc: Exception,
    context: str = "",
    user_id: Optional[str] = None
) -> WecomAssistantException:
    """
    统一异常处理函数
    
    Args:
        exc: 原始异常
        context: 异常发生的上下文
        user_id: 用户ID（用于日志追踪）
    
    Returns:
        WecomAssistantException: 包装后的异常
    """
    if isinstance(exc, WecomAssistantException):
        return exc
    
    # 根据异常类型进行分类处理
    error_message = str(exc)
    
    if "signature" in error_message.lower():
        return WecomException(
            message=f"企业微信签名验证失败: {error_message}",
            error_code=ErrorCode.WECOM_SIGNATURE_INVALID,
            details={"context": context, "user_id": user_id},
            user_message="系统验证失败，请联系管理员。"
        )
    
    if "timeout" in error_message.lower():
        return LLMException(
            message=f"LLM调用超时: {error_message}",
            error_code=ErrorCode.LLM_TIMEOUT,
            details={"context": context, "user_id": user_id},
            user_message="处理时间较长，请稍后再试。"
        )
    
    if "quota" in error_message.lower() or "rate" in error_message.lower():
        return LLMException(
            message=f"LLM配额不足: {error_message}",
            error_code=ErrorCode.LLM_QUOTA_EXCEEDED,
            details={"context": context, "user_id": user_id},
            user_message="系统繁忙，请稍后再试。"
        )
    
    if "network" in error_message.lower() or "connection" in error_message.lower():
        return WecomAssistantException(
            message=f"网络连接错误: {error_message}",
            error_code=ErrorCode.NETWORK_ERROR,
            details={"context": context, "user_id": user_id},
            user_message="网络连接异常，请稍后再试。"
        )
    
    # 默认处理
    return WecomAssistantException(
        message=f"未知错误 in {context}: {error_message}",
        error_code=ErrorCode.UNKNOWN_ERROR,
        details={"context": context, "user_id": user_id, "original_type": type(exc).__name__}
    )


class ErrorReporter:
    """错误报告器，用于收集和报告错误统计"""
    
    def __init__(self):
        self.error_counts = {}
    
    def report_error(self, exception: WecomAssistantException):
        """报告错误"""
        error_code = exception.error_code.value
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
    
    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计"""
        return self.error_counts.copy()
    
    def reset_stats(self):
        """重置统计"""
        self.error_counts.clear()


# 全局错误报告器实例
error_reporter = ErrorReporter()