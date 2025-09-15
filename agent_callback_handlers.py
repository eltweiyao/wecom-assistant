from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage
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

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        print(f"on_chat_model_start serialized {messages}")
        print(f"on_chat_model_start metadata {metadata}")
        print(f"on_chat_model_start kwargs {kwargs}")


    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        print(f"on_chat_model_start serialized {inputs}")
        print(f"on_chat_model_start metadata {metadata}")
        print(f"on_chat_model_start kwargs {kwargs}")


    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        print(f"on_chain_end output {outputs}")
        print(f"on_chain_end kwargs {kwargs}")

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        print(f"on_llm_start serialized {serialized}")
        print(f"on_llm_start prompts {prompts}")
        print(f"on_llm_start metadata {metadata}")
        print(f"on_llm_start kwargs {kwargs}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        print(f"on_llm_new_token {token}")
        print(f"on_llm_new_token kwargs {kwargs}")


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
