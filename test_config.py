"""
配置模块单元测试
"""
import pytest
import os
from unittest.mock import patch
from config import Config
from exceptions import ConfigException


class TestConfig:
    """配置管理测试类"""
    
    def test_config_with_all_required_vars(self):
        """测试所有必需环境变量都存在的情况"""
        with patch.dict(os.environ, {
            'WECOM_CORP_ID': 'test_corp_id',
            'WECOM_AGENT_ID': 'test_agent_id',
            'WECOM_SECRET': 'test_secret',
            'WECOM_TOKEN': 'test_token',
            'WECOM_ENCODING_AES_KEY': 'test_aes_key',
            'OPENAI_API_KEY': 'test_api_key'
        }):
            config = Config()
            assert config.WECOM_CORP_ID == 'test_corp_id'
            assert config.WECOM_AGENT_ID == 'test_agent_id'
            assert config.OPENAI_API_KEY == 'test_api_key'
    
    def test_config_missing_required_vars(self):
        """测试缺少必需环境变量的情况"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigException) as exc_info:
                Config()
            assert "Missing required configuration" in str(exc_info.value)
    
    def test_config_default_values(self):
        """测试默认值设置"""
        with patch.dict(os.environ, {
            'WECOM_CORP_ID': 'test_corp_id',
            'WECOM_AGENT_ID': 'test_agent_id',
            'WECOM_SECRET': 'test_secret',
            'WECOM_TOKEN': 'test_token',
            'WECOM_ENCODING_AES_KEY': 'test_aes_key',
            'OPENAI_API_KEY': 'test_api_key'
        }):
            config = Config()
            assert config.LLM_MODEL_NAME == "qwen-max"
            assert config.VISION_MODEL_NAME == "qwen-vl-max"
            assert config.REQUEST_TIMEOUT == 30
            assert config.MAX_CONCURRENT_REQUESTS == 10
    
    def test_config_custom_values(self):
        """测试自定义配置值"""
        with patch.dict(os.environ, {
            'WECOM_CORP_ID': 'test_corp_id',
            'WECOM_AGENT_ID': 'test_agent_id',
            'WECOM_SECRET': 'test_secret',
            'WECOM_TOKEN': 'test_token',
            'WECOM_ENCODING_AES_KEY': 'test_aes_key',
            'OPENAI_API_KEY': 'test_api_key',
            'LLM_MODEL_NAME': 'custom_model',
            'REQUEST_TIMEOUT': '60',
            'LOG_LEVEL': 'DEBUG'
        }):
            config = Config()
            assert config.LLM_MODEL_NAME == "custom_model"
            assert config.REQUEST_TIMEOUT == 60
            assert config.LOG_LEVEL == "DEBUG"
    
    def test_config_summary(self):
        """测试配置摘要功能"""
        with patch.dict(os.environ, {
            'WECOM_CORP_ID': 'test_corp_id',
            'WECOM_AGENT_ID': 'test_agent_id',
            'WECOM_SECRET': 'test_secret',
            'WECOM_TOKEN': 'test_token',
            'WECOM_ENCODING_AES_KEY': 'test_aes_key',
            'OPENAI_API_KEY': 'test_api_key',
            'OPENAI_API_BASE': 'https://api.example.com'
        }):
            config = Config()
            summary = config.get_config_summary()
            
            assert summary['wecom_configured'] == True
            assert summary['llm_model'] == 'qwen-max'
            assert summary['api_base_configured'] == True
            assert 'request_timeout' in summary
            assert 'max_concurrent_requests' in summary


if __name__ == '__main__':
    pytest.main([__file__])