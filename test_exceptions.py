"""
异常处理模块单元测试
"""
import pytest
from exceptions import (
    WecomAssistantException, WecomException, LLMException, ToolException,
    ErrorCode, handle_exception, error_reporter
)


class TestExceptions:
    """异常处理测试类"""
    
    def test_wecom_assistant_exception_creation(self):
        """测试基础异常创建"""
        exc = WecomAssistantException(
            message="Test error",
            error_code=ErrorCode.UNKNOWN_ERROR,
            details={"key": "value"},
            user_message="用户友好的错误信息"
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == ErrorCode.UNKNOWN_ERROR
        assert exc.details == {"key": "value"}
        assert exc.user_message == "用户友好的错误信息"
        assert exc.traceback is not None
    
    def test_specific_exception_types(self):
        """测试特定异常类型"""
        wecom_exc = WecomException("WeChat error", ErrorCode.WECOM_API_ERROR)
        llm_exc = LLMException("LLM error", ErrorCode.LLM_API_ERROR)
        tool_exc = ToolException("Tool error", ErrorCode.TOOL_EXECUTION_ERROR)
        
        assert isinstance(wecom_exc, WecomAssistantException)
        assert isinstance(llm_exc, WecomAssistantException)
        assert isinstance(tool_exc, WecomAssistantException)
    
    def test_handle_exception_signature_error(self):
        """测试处理签名验证错误"""
        original_exc = Exception("Invalid signature detected")
        wrapped = handle_exception(original_exc, "test_context", "user123")
        
        assert isinstance(wrapped, WecomException)
        assert wrapped.error_code == ErrorCode.WECOM_SIGNATURE_INVALID
        assert "user123" in str(wrapped.details)
    
    def test_handle_exception_timeout_error(self):
        """测试处理超时错误"""
        original_exc = Exception("Request timeout occurred")
        wrapped = handle_exception(original_exc, "test_context")
        
        assert isinstance(wrapped, LLMException)
        assert wrapped.error_code == ErrorCode.LLM_TIMEOUT
    
    def test_handle_exception_quota_error(self):
        """测试处理配额错误"""
        original_exc = Exception("Rate limit exceeded")
        wrapped = handle_exception(original_exc, "test_context")
        
        assert isinstance(wrapped, LLMException)
        assert wrapped.error_code == ErrorCode.LLM_QUOTA_EXCEEDED
    
    def test_handle_exception_network_error(self):
        """测试处理网络错误"""
        original_exc = Exception("Network connection failed")
        wrapped = handle_exception(original_exc, "test_context")
        
        assert wrapped.error_code == ErrorCode.NETWORK_ERROR
    
    def test_handle_exception_unknown_error(self):
        """测试处理未知错误"""
        original_exc = Exception("Some random error")
        wrapped = handle_exception(original_exc, "test_context")
        
        assert wrapped.error_code == ErrorCode.UNKNOWN_ERROR
        assert "Some random error" in wrapped.message
    
    def test_handle_exception_already_wrapped(self):
        """测试处理已包装的异常"""
        original_exc = WecomException("Already wrapped", ErrorCode.WECOM_API_ERROR)
        wrapped = handle_exception(original_exc, "test_context")
        
        # 应该返回原异常，不做二次包装
        assert wrapped is original_exc
    
    def test_error_reporter(self):
        """测试错误报告器"""
        # 重置错误统计
        error_reporter.reset_stats()
        
        # 报告一些错误
        exc1 = WecomException("Error 1", ErrorCode.WECOM_API_ERROR)
        exc2 = WecomException("Error 2", ErrorCode.WECOM_API_ERROR)
        exc3 = LLMException("Error 3", ErrorCode.LLM_TIMEOUT)
        
        error_reporter.report_error(exc1)
        error_reporter.report_error(exc2)
        error_reporter.report_error(exc3)
        
        # 检查统计
        stats = error_reporter.get_error_stats()
        assert stats[ErrorCode.WECOM_API_ERROR.value] == 2
        assert stats[ErrorCode.LLM_TIMEOUT.value] == 1
        
        # 重置统计
        error_reporter.reset_stats()
        stats = error_reporter.get_error_stats()
        assert len(stats) == 0


class TestErrorCodes:
    """错误代码测试类"""
    
    def test_error_code_enum(self):
        """测试错误代码枚举"""
        assert ErrorCode.WECOM_SIGNATURE_INVALID.value == "WECOM_001"
        assert ErrorCode.LLM_API_ERROR.value == "LLM_001"
        assert ErrorCode.TOOL_EXECUTION_ERROR.value == "TOOL_001"
        assert ErrorCode.UNKNOWN_ERROR.value == "SYS_999"
    
    def test_error_code_uniqueness(self):
        """测试错误代码唯一性"""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes))  # 确保没有重复


if __name__ == '__main__':
    pytest.main([__file__])