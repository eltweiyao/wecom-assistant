import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 企业微信配置
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID")
WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID")
WECOM_SECRET = os.getenv("WECOM_SECRET")
WECOM_TOKEN = os.getenv("WECOM_TOKEN")
WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")

# 大语言模型配置
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_VISION_BASE = os.getenv("OPENAI_API_VISION_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen-max")
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "qwen-vl-max")