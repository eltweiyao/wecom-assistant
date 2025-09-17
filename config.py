import os
from typing import Optional
from dotenv import load_dotenv
from exceptions import ConfigException, ErrorCode

# 加载 .env 文件中的环境变量
load_dotenv()

class Config:
    """配置管理类，提供统一的配置访问和验证"""
    
    def __init__(self):
        self._validate_required_configs()
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """安全地获取环境变量"""
        value = os.getenv(key, default)
        if required and not value:
            raise ConfigException(
                f"Required environment variable {key} is not set",
                ErrorCode.CONFIG_ERROR,
                user_message="系统配置错误，请联系管理员。"
            )
        return value or (default or "")
    
    def _validate_required_configs(self):
        """验证必需的配置项"""
        required_configs = [
            'WECOM_CORP_ID',
            'WECOM_AGENT_ID', 
            'WECOM_SECRET',
            'WECOM_TOKEN',
            'WECOM_ENCODING_AES_KEY',
            'OPENAI_API_KEY'
        ]
        
        missing_configs = []
        for config_key in required_configs:
            if not os.getenv(config_key):
                missing_configs.append(config_key)
        
        if missing_configs:
            raise ConfigException(
                f"Missing required configuration: {', '.join(missing_configs)}",
                ErrorCode.CONFIG_ERROR,
                details={"missing_configs": missing_configs},
                user_message="系统配置不完整，请联系管理员。"
            )
    
    # 企业微信配置
    @property
    def WECOM_CORP_ID(self) -> str:
        return self._get_env("WECOM_CORP_ID", required=True)
    
    @property
    def WECOM_AGENT_ID(self) -> str:
        return self._get_env("WECOM_AGENT_ID", required=True)
    
    @property
    def WECOM_SECRET(self) -> str:
        return self._get_env("WECOM_SECRET", required=True)
    
    @property
    def WECOM_TOKEN(self) -> str:
        return self._get_env("WECOM_TOKEN", required=True)
    
    @property
    def WECOM_ENCODING_AES_KEY(self) -> str:
        return self._get_env("WECOM_ENCODING_AES_KEY", required=True)
    
    # 大语言模型配置
    @property
    def OPENAI_API_BASE(self) -> Optional[str]:
        return os.getenv("OPENAI_API_BASE")
    
    @property
    def OPENAI_API_VISION_BASE(self) -> Optional[str]:
        return os.getenv("OPENAI_API_VISION_BASE")
    
    @property
    def OPENAI_API_KEY(self) -> str:
        return self._get_env("OPENAI_API_KEY", required=True)
    
    @property
    def LLM_MODEL_NAME(self) -> str:
        return self._get_env("LLM_MODEL_NAME", default="qwen-max")
    
    @property
    def VISION_MODEL_NAME(self) -> str:
        return self._get_env("VISION_MODEL_NAME", default="qwen-vl-max")
    
    @property
    def EMBEDDING_MODEL_NAME(self) -> str:
        return self._get_env("EMBEDDING_MODEL_NAME", default="text-embedding-v2")
    
    @property
    def DASHSCOPE_API_KEY(self) -> Optional[str]:
        return os.getenv("DASHSCOPE_API_KEY")
    
    # 性能配置
    @property
    def REQUEST_TIMEOUT(self) -> int:
        timeout_str = self._get_env("REQUEST_TIMEOUT", default="30")
        return int(timeout_str)
    
    @property
    def MAX_CONCURRENT_REQUESTS(self) -> int:
        max_requests_str = self._get_env("MAX_CONCURRENT_REQUESTS", default="10")
        return int(max_requests_str)
    
    @property
    def LOG_LEVEL(self) -> str:
        return self._get_env("LOG_LEVEL", default="INFO")
    
    def get_config_summary(self) -> dict:
        """获取配置摘要（隐藏敏感信息）"""
        return {
            "wecom_configured": bool(self.WECOM_CORP_ID),
            "llm_model": self.LLM_MODEL_NAME,
            "vision_model": self.VISION_MODEL_NAME,
            "api_base_configured": bool(self.OPENAI_API_BASE),
            "request_timeout": self.REQUEST_TIMEOUT,
            "max_concurrent_requests": self.MAX_CONCURRENT_REQUESTS,
            "log_level": self.LOG_LEVEL
        }

# 创建全局配置实例
config = Config()

# 为了保持向后兼容，导出属性
WECOM_CORP_ID = config.WECOM_CORP_ID
WECOM_AGENT_ID = config.WECOM_AGENT_ID
WECOM_SECRET = config.WECOM_SECRET
WECOM_TOKEN = config.WECOM_TOKEN
WECOM_ENCODING_AES_KEY = config.WECOM_ENCODING_AES_KEY
OPENAI_API_BASE = config.OPENAI_API_BASE
OPENAI_API_VISION_BASE = config.OPENAI_API_VISION_BASE
OPENAI_API_KEY = config.OPENAI_API_KEY
LLM_MODEL_NAME = config.LLM_MODEL_NAME
VISION_MODEL_NAME = config.VISION_MODEL_NAME
EMBEDDING_MODEL_NAME = config.EMBEDDING_MODEL_NAME
DASHSCOPE_API_KEY = config.DASHSCOPE_API_KEY