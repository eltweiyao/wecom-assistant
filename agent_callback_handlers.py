import time
import uuid
from typing import Any, Dict, List

from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

class TokenUsageCallbackHandler(BaseCallbackHandler):
    """
    一个用于统计和记录LLM Token使用量的自定义回调处理器。

    功能:
    - 在每次LLM调用结束时自动累加Token消耗。
    - 分别记录 prompt, completion, 和 total tokens。
    - 兼容返回格式中可能缺少某些字段的情况（例如，某些模型可能不返回 prompt_tokens）。
    - 提供一个易于阅读的打印格式。
    """

    def __init__(self) -> None:
        super().__init__()
        # 初始化各项Token计数器
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        print(f"on_llm_end response {response}")
        print(f"on_llm_end kwargs {kwargs}")

        """
        在每次LLM调用结束时被自动调用。

        Args:
            response (LLMResult): LLM调用的结果对象，包含了生成内容和元数据。
        """
        # 从llm_output中获取token_usage信息
        # response.llm_output 是一个字典，包含了特定于LLM提供商的原始返回信息
        token_usage = response.llm_output.get("token_usage", {})

        # 确保token_usage是一个字典
        if isinstance(token_usage, dict):
            # 使用 .get(key, 0) 方法安全地获取值，如果键不存在则默认为0
            self.prompt_tokens += token_usage.get("prompt_tokens", 0)
            self.completion_tokens += token_usage.get("completion_tokens", 0)
            self.total_tokens += token_usage.get("total_tokens", 0)

    def __repr__(self) -> str:
        """当打印该对象时，返回一个格式化的字符串，方便查看结果。"""
        return (
            f"--- Token Usage Report ---\n"
            f"Prompt tokens:     {self.prompt_tokens}\n"
            f"Completion tokens: {self.completion_tokens}\n"
            f"Total tokens:      {self.total_tokens}\n"
            f"--------------------------"
        )

    def reset(self) -> None:
        """重置所有计数器，方便在多次独立调用中复用同一个handler实例。"""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0


class DetailedTimingCallbackHandler(BaseCallbackHandler):
    """一个用于统计 Agent Executor、LLM、Tool 详细耗时的回调处理器"""

    def __init__(self):
        super().__init__()
        # 使用字典来处理可能并发或嵌套的调用
        self.start_times: Dict[uuid.UUID, float] = {}

        # 用于存储和汇总耗时
        self.agent_total_time: float = 0.0
        self.llm_total_time: float = 0.0
        self.tool_total_time: float = 0.0
        self.llm_calls: int = 0
        self.tool_calls: int = 0

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: uuid.UUID, **kwargs: Any
    ) -> None:
        """在 Agent Executor 主链开始时被调用"""
        # if serialized.get("name") == agent_executor.name:
        print(f"\n{'=' * 20} Agent Start {'=' * 20}")
        self.start_times[run_id] = time.perf_counter()


def on_chain_end(self, outputs: Dict[str, Any], *, run_id: uuid.UUID, **kwargs: Any) -> None:
    """在 Agent Executor 主链结束时被调用"""
    if run_id in self.start_times:
        start_time = self.start_times.pop(run_id)
        end_time = time.perf_counter()
        self.agent_total_time = end_time - start_time
        print(f"\n{'=' * 20} Agent End {'=' * 20}")
        print(f"Agent Total Time: {self.agent_total_time:.4f} seconds")


def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], *, run_id: uuid.UUID, **kwargs: Any
) -> None:
    """在 LLM 调用开始时被调用"""
    print(f"\n\t[LLM Call] Start...")
    self.start_times[run_id] = time.perf_counter()


def on_llm_end(self, response: LLMResult, *, run_id: uuid.UUID, **kwargs: Any) -> None:
    """在 LLM 调用结束时被调用"""
    if run_id in self.start_times:
        start_time = self.start_times.pop(run_id)
        end_time = time.perf_counter()
        duration = end_time - start_time
        self.llm_total_time += duration
        self.llm_calls += 1
        print(f"\t[LLM Call] End. Duration: {duration:.4f} seconds")


def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, *, run_id: uuid.UUID, **kwargs: Any
) -> None:
    """在 Tool 调用开始时被调用"""
    # 注意：这里的 `on_tool_start` 发生在工具的实际执行之前
    # 我们将在 `get_word_length` 函数内部打印来更好地展示
    self.start_times[run_id] = time.perf_counter()


def on_tool_end(self, output: str, *, run_id: uuid.UUID, **kwargs: Any) -> None:
    """在 Tool 调用结束时被调用"""
    if run_id in self.start_times:
        start_time = self.start_times.pop(run_id)
        end_time = time.perf_counter()
        duration = end_time - start_time
        self.tool_total_time += duration
        self.tool_calls += 1
        print(f"\t[Tool Timing] Tool execution and processing duration: {duration:.4f} seconds")


def get_summary(self) -> Dict[str, Any]:
    """获取所有耗时的汇总信息"""
    return {
        "agent_total_time": self.agent_total_time,
        "total_llm_calls": self.llm_calls,
        "llm_total_time": self.llm_total_time,
        "total_tool_calls": self.tool_calls,
        "tool_total_time": self.tool_total_time
    }
