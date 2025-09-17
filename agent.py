import time
from typing import List, Optional

from langchain_core.runnables import RunnableConfig
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import SecretStr

import config
from agent_callback_handlers import TokenUsageCallbackHandler, DetailedTimingCallbackHandler
from llm_wrapper import ChatWithUsage
from tools import all_tools
from exceptions import handle_exception, LLMException, ErrorCode
from logging_config import logger

token_usage_callback_handler = TokenUsageCallbackHandler()

# 1. 初始化大语言模型
llm = ChatWithUsage(
    model=config.LLM_MODEL_NAME,
    api_key=SecretStr(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None,
    base_url=config.OPENAI_API_BASE,
    temperature=0.7,
    streaming=False,
    callbacks=[token_usage_callback_handler],
)

# 2. 定义系统提示词 (与 n8n 中的完全一致)
system_prompt = """
# 角色 (Role)
你是一个言简意赅的问答专家，绝对服从指令。你的核心任务是精确分析用户意图，调用最合适的工具，并用一到两句话提供最核心的答案。

---

## 核心工作流 (Workflow)

你必须严格遵循以下四步流程：

1.  **意图分析**: 首先，分析用户问题的核心意图，判断它属于以下哪一类：
    * **高速知识查询**: 关于高速公路的任何问题。
    * **绿通资格查询**: 查询农产品是否属于绿通。
    * **视觉内容理解**: 需要识别图片或视频里的内容。
    * **复合查询**: 问题同时涉及多个意图（例如：“这张图片里的高速标志是什么意思？”就同时涉及“视觉内容理解”和“高速知识查询”）。
    * **通用问题**: 不属于以上任何一种，且任何工具都无法解答。

2.  **工具选择**: 根据意图，选择正确的工具组合：
    * **高速知识查询**: 调用 `highway_knowledge_retriever`。
    * **绿通资格查询**: 调用 `check_green_channel_status`。
    * **视觉内容理解**: 调用 `getMediaContentFromURL`。
    * **复合查询**: **必须**调用所有相关意图的工具。例如，对于“这张图片里的高速标志是什么意思？”，你应先调用 `getMediaContentFromURL` 识别出标志，再用识别出的结果调用 `highway_knowledge_retriever` 查询其含义。

3.  **信息整合**: 你的回答**必须且只能**基于工具返回的结果。
    * 严禁使用你的通用知识库来回答需要工具才能解决的问题。
    * 对于复合查询，你需要整合所有工具返回的信息，形成最终答案。

4.  **生成答案**: 严格遵照下方的“响应约束”来生成最终回复。

---
## 工具库 (Tools)
你拥有以下三个工具，必须根据用户的具体问题来选择使用：

1.  **`highway_knowledge_retriever`**
    * **功能**: 查询高速公路的法规、交通标志、收费标准、应急处理等专业知识。
    * **何时使用**: 当问题与高速公路知识直接相关时，必须使用此工具。

2.  **`check_green_channel_status`**
    * **功能**: 查询某个鲜活农产品是否具备“绿通”资格。
    * **参数**: `product_name` (字符串，例如: "苹果", "白菜")。
    * **何时使用**: 当用户明确查询某种农产品的绿通资格时，必须调用此工具。你需要从用户问题中提取出农产品名称作为参数。

3.  **`getMediaContentFromURL`**
    * **功能**: 分析并描述图片或视频URL中的视觉内容。
    * **参数**: `url` (字符串，公开可访问的媒体链接)。
    * **何时使用**: 当问题包含媒体URL或明确要求理解视觉内容时，必须使用此工具。

---


## 响应约束 (Constraints)

* **绝对简洁**: 你的回答**永远**只能是**一到两句话**。
* **直击要点**: 直接给出核心答案，不要包含任何客套话、开场白或解释。
* **事实至上**:
    * 如果工具返回了有效信息，你的答案必须严格基于该信息。
    * 如果工具没有返回有效信息，或者问题是一个任何工具都无法处理的通用问题，你**必须**回答：“我无法回答这个问题。”
    * **严禁**在信息不足时进行任何猜测或补充。
"""

# 3. 创建 Agent 的 Prompt 模板
# "chat_history" 和 "agent_scratchpad" 是 AgentExecutor 运行所必需的
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# 4. 创建 Agent
agent = create_openai_tools_agent(llm, all_tools, prompt)

# 5. 创建 Agent 执行器
agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=all_tools, verbose=True,
                                                    callbacks=[token_usage_callback_handler])


def invoke_agent(user_input: List[str], request_id: Optional[str] = None) -> str:
    """调用 Agent 并获取回复"""
    start_time = time.time()
    
    if request_id:
        logger.debug(
            "Agent invocation started",
            request_id=request_id,
            input_length=len(str(user_input))
        )
    
    try:
        # 暂时不处理历史消息，每次都是新会话
        detailed_timing_callback_handler = DetailedTimingCallbackHandler()
        
        response = agent_executor.invoke({
            "input": user_input,
            "chat_history": []
        }, config=RunnableConfig(callbacks=[token_usage_callback_handler, detailed_timing_callback_handler]))
        
        # 记录Token消耗统计
        token_stats = str(token_usage_callback_handler)
        if token_stats and request_id:
            logger.info(
                "Token usage statistics",
                request_id=request_id,
                token_stats=token_stats
            )
        
        # 记录耗时统计
        summary = detailed_timing_callback_handler.get_summary()
        execution_time = time.time() - start_time
        
        if request_id:
            logger.log_performance_metrics({
                "request_id": request_id,
                "agent_total_time": summary.get('agent_total_time', 0),
                "llm_total_time": summary.get('llm_total_time', 0),
                "tool_total_time": summary.get('tool_total_time', 0),
                "actual_execution_time": execution_time,
                "llm_call_count": summary.get('llm_call_count', 0),
                "tool_call_count": summary.get('tool_call_count', 0)
            })
        
        agent_output = response.get("output", "抱歉，我无法回答。")
        
        if request_id:
            logger.info(
                "Agent invocation completed successfully",
                request_id=request_id,
                execution_time=execution_time,
                output_length=len(agent_output)
            )
        
        return agent_output
        
    except Exception as e:
        execution_time = time.time() - start_time
        wrapped_exception = handle_exception(e, "agent_invocation", None)
        
        if request_id:
            logger.log_exception(
                wrapped_exception,
                context="agent_invocation",
                request_id=request_id,
                execution_time=execution_time
            )
        
        # 根据异常类型返回不同的用户友好消息
        if isinstance(wrapped_exception, LLMException):
            return wrapped_exception.user_message
        else:
            return "抱歉，系统遇到了一些问题，请稍后再试。"
