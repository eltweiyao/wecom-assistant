from langchain_openai import ChatOpenAI

class ChatWithUsage(ChatOpenAI):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        if hasattr(result, "llm_output") and result.llm_output:
            usage = result.llm_output.get("token_usage")
            if usage:
                # 在这里统计 token
                print("Usage:", usage)
        return result