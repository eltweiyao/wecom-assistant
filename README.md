# 企业微信智能助手 - 优化后的项目文档

## 📋 项目概述

本项目是一个基于 FastAPI 的企业微信智能助手，集成了大语言模型(LLM)和多种工具，能够自动处理企业微信消息并提供智能回复。

### 🚀 主要特性

- **企业微信集成**：支持企业微信应用和客服消息处理
- **LLM集成**：支持多种大语言模型（通义千问、GPT等）
- **多模态支持**：支持文本、图片、视频等多种消息类型
- **工具集成**：内置绿通查询、媒体内容分析等专业工具
- **性能监控**：完整的性能指标收集和健康检查
- **结构化日志**：JSON格式的结构化日志记录
- **错误处理**：统一的异常处理和用户友好的错误提示
- **配置管理**：安全的环境变量配置管理

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   企业微信客户端   │───▶│   FastAPI服务    │───▶│   Agent执行器    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   性能监控模块    │    │    LLM + 工具    │
                       └─────────────────┘    └─────────────────┘
```

## 📁 项目结构

```
wecom-assistant/
├── main.py                    # FastAPI主应用入口
├── agent.py                   # Agent逻辑和LLM调用
├── wecom_handler.py           # 企业微信API处理
├── tools.py                   # 工具集合（视觉分析、绿通查询等）
├── config.py                  # 配置管理（新增）
├── exceptions.py              # 异常处理（新增）
├── logging_config.py          # 日志系统（新增）
├── monitoring.py              # 性能监控（新增）
├── agent_callback_handlers.py # Agent回调处理器
├── llm_wrapper.py             # LLM包装器
├── rag.py                     # RAG检索（暂未启用）
├── requirements.txt           # 依赖列表
├── .env.example              # 环境配置模板（新增）
└── logs/                     # 日志文件目录（自动创建）
    ├── wecom_assistant.log   # 主日志文件
    └── error.log             # 错误日志文件
```

## ⚙️ 快速开始

### 1. 环境准备

```bash
# 克隆项目（如果适用）
git clone <repository-url>
cd wecom-assistant

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入真实配置
# 必填配置项：
# - WECOM_CORP_ID: 企业微信企业ID
# - WECOM_AGENT_ID: 应用ID  
# - WECOM_SECRET: 应用Secret
# - WECOM_TOKEN: 回调验证Token
# - WECOM_ENCODING_AES_KEY: 消息加解密密钥
# - OPENAI_API_KEY: LLM API密钥
```

### 3. 启动服务

```bash
# 开发模式启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式启动
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 性能指标
curl http://localhost:8000/metrics
```

## 🔧 配置说明

### 企业微信配置

1. **获取企业ID**：企业微信管理后台 → 我的企业 → 企业信息
2. **创建应用**：企业微信管理后台 → 应用管理 → 创建应用
3. **配置回调**：应用详情 → 接收消息 → 设置API接收
   - 回调URL: `https://your-domain.com/wechat-agent-callback`
   - Token: 自定义字符串
   - EncodingAESKey: 自动生成或手动设置

### LLM配置

支持多种LLM服务：
- **通义千问**：使用DashScope API
- **OpenAI**：使用OpenAI API
- **其他兼容服务**：任何OpenAI兼容的API

## 📊 监控和日志

### 健康检查端点

- **URL**: `GET /health`
- **功能**: 检查系统健康状态
- **返回**: JSON格式的健康检查结果

### 性能指标端点

- **URL**: `GET /metrics`  
- **功能**: 获取详细的性能指标
- **包含内容**:
  - 请求统计（总数、成功率、响应时间等）
  - 系统资源使用情况（CPU、内存、磁盘）
  - LLM调用统计
  - 工具使用统计

### 日志系统

项目使用结构化JSON日志，所有日志都会输出到：
- **控制台**：实时查看
- **文件**：`logs/wecom_assistant.log`（所有级别）
- **错误文件**：`logs/error.log`（仅错误级别）

日志包含的信息：
- 时间戳
- 日志级别
- 模块信息
- 用户ID（如果适用）
- 请求ID（用于追踪）
- 执行时间
- 错误堆栈（如果有错误）

## 🛠️ 开发指南

### 添加新工具

1. 在 `tools.py` 中定义新的工具函数
2. 使用 `@tool` 装饰器
3. 添加到 `all_tools` 列表
4. 更新Agent的系统提示词

示例：
```python
@tool
def my_new_tool(query: str) -> str:
    """工具描述"""
    try:
        # 工具逻辑
        result = do_something(query)
        logger.log_tool_call("my_new_tool", time.time(), True)
        return result
    except Exception as e:
        logger.log_tool_call("my_new_tool", time.time(), False)
        raise ToolException(f"工具执行失败: {e}")
```

### 添加健康检查

```python
from monitoring import health_checker

def my_health_check():
    # 检查逻辑
    if check_something():
        return HealthCheckResult(
            name="my_check",
            status="healthy", 
            message="Everything OK"
        )
    else:
        return HealthCheckResult(
            name="my_check",
            status="unhealthy",
            message="Something wrong"
        )

health_checker.register_check("my_check", my_health_check)
```

## 🚨 故障排除

### 常见问题

1. **企业微信回调验证失败**
   - 检查Token和EncodingAESKey配置
   - 确认URL可以公网访问
   - 查看日志中的具体错误信息

2. **LLM调用失败**
   - 检查API密钥是否正确
   - 验证API端点是否可访问
   - 查看API配额是否充足

3. **工具执行失败**
   - 检查工具依赖的外部资源
   - 查看工具执行日志
   - 验证输入参数格式

### 性能优化建议

1. **并发限制**：通过 `MAX_CONCURRENT_REQUESTS` 控制并发
2. **超时设置**：合理设置 `REQUEST_TIMEOUT`
3. **缓存策略**：对频繁查询的数据进行缓存
4. **资源监控**：定期查看 `/metrics` 端点的资源使用情况

## 📈 版本更新记录

### v2.0.0 (优化版本)

**新增功能：**
- ✅ 统一异常处理机制
- ✅ 结构化JSON日志系统  
- ✅ 强化配置管理和验证
- ✅ 性能监控和健康检查
- ✅ 完整的错误追踪和报告
- ✅ 用户友好的错误提示

**架构改进：**
- ✅ 模块化代码结构
- ✅ 类型安全和类型提示
- ✅ 更好的错误边界处理
- ✅ 请求链路追踪

**监控增强：**
- ✅ 实时性能指标收集
- ✅ 系统资源监控
- ✅ 自动健康检查
- ✅ 请求成功率统计

## 📞 技术支持

如果遇到问题，可以通过以下方式获取帮助：

1. **查看日志**：检查 `logs/` 目录下的日志文件
2. **健康检查**：访问 `/health` 端点查看系统状态
3. **性能监控**：访问 `/metrics` 端点查看详细指标

## 📄 许可证

本项目采用 MIT 许可证。