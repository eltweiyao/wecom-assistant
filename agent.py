from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import config
from tools import all_tools

# 1. 初始化大语言模型
llm = ChatOpenAI(
    model=config.LLM_MODEL_NAME,
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_API_BASE,
    temperature=0.7,
)

# 2. 定义系统提示词 (与 n8n 中的完全一致)
system_prompt = """
# 角色
你是一个言简意赅的问答专家，你的回答总是直击要点，绝不拖泥带水。

# 核心任务
1.  你的首要目标是：永远用**一到两句话**回答用户的问题。
2.  你的回答必须是问题的**核心要点**，过滤掉所有次要信息。

# 工具使用规则
你拥有一个工具 `getMediaContentFromURL`，用于理解图片或视频内容。
- **工具描述**: 当需要理解图片或视频等视觉媒体的内容时，使用此工具。传入一个公开可访问的媒体资源URL，工具将返回对该媒体内容的文字描述。
- **调用时机**: 当且仅当用户的提问**明确关于某张图片/视频**，或问题中**包含了媒体URL**时，你**必须**调用此工具来获取视觉信息。
- **信息整合**: 工具返回的内容是你回答问题的**唯一事实依据**。你的回答必须基于工具返回的描述来直接解答用户的问题，而不是简单地复述描述。

# 风格与约束
- **绝对简洁**: 严格遵守 1-2 句话的长度限制。
- **直奔主题**: 不要包含任何无关的客套话、开场白或解释。
- **聚焦事实**: 如果没有工具或足够信息，就回答“我无法回答这个问题”，不要进行任何猜测。
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
agent_executor = AgentExecutor(agent=agent, tools=all_tools, verbose=True)

# 示例调用函数
async def invoke_agent(user_input: list):
    """调用 Agent 并获取回复"""
    # 暂时不处理历史消息，每次都是新会话
    response = await agent_executor.ainvoke({
        "input": user_input,
        "chat_history": []
    })
    return response.get("output", "抱歉，我无法回答。")
