# tools.py
import base64
import requests
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import config

# 初始化一个专门用于视觉分析的 LLM 客户端
# 我们在这里单独初始化，因为它使用了与主 Agent 不同的模型
try:
    vision_llm = ChatOpenAI(
        model=config.VISION_MODEL_NAME,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_API_BASE,
        temperature=0,  # 视觉分析任务通常需要更确定的结果
    )
except ImportError:
    print("无法导入 ChatOpenAI，请确保 langchain-openai 已安装")
    vision_llm = None


@tool
def get_media_content_from_url(media_url: str) -> str:
    """
    当需要理解图片或视频等视觉媒体的内容时，使用此工具。
    传入一个公开可访问的媒体资源URL，工具将返回对该媒体内容的文字描述。
    这对于回答任何关于视觉信息的问题至关重要。
    """
    if not vision_llm:
        return "视觉分析工具未正确初始化。"

    print(f"--- [Tool Called] Starting analysis for URL: {media_url} ---")

    try:
        # 1. 下载媒体文件
        # 设置超时以避免长时间等待
        response = requests.get(media_url, stream=True, timeout=20)
        response.raise_for_status()  # 如果下载失败 (如 404), 则会抛出异常

        # 2. 将二进制内容编码为 Base64
        # 为了效率，我们只读取前 10MB 的数据，防止文件过大
        # max_size = 10 * 1024 * 1024  # 10MB
        # content = response.raw.read(max_size)
        content = response.raw.read()
        base64_encoded_content = base64.b64encode(content).decode("utf-8")

        # 从响应头获取 MIME 类型 (e.g., 'image/jpeg')
        mime_type = response.headers.get("Content-Type", "image/jpeg")
        print(f"--- Downloaded {len(content)} bytes, MIME type: {mime_type} ---")

        # 3. 构造 LangChain 多模态消息
        # 这是调用视觉模型的标准格式
        prompt_text = """
你是一个专业的视觉分析引擎。你的任务是精确、客观地描述所提供的图片或视频内容。请严格遵循以下规则：

1.  **识别核心元素**：清晰地列出图片或视频中的所有关键元素，包括：
    * **人物**：数量、大致年龄、性别、着装、姿态、表情和正在做的动作。
    * **物体**：主要和次要的物体，以及它们的品牌、状态或特征。
    * **场景**：描述环境是在室内还是室外，是城市街道、自然风光、办公室还是其他特定地点。
    * **文字**：识别并提取任何清晰可见的文字、标志或符号。

2.  **描述动态行为（仅视频）**：如果输入是视频，请按时间顺序简要概括发生的核心事件、人物的主要行为和场景的显著变化。

3.  **保持客观中立**：只描述你看到的客观事实。请勿进行任何主观解读、情感猜测、背景联想或价值判断。

4.  **输出格式**：使用简洁、直接的语言，以要点形式进行描述，方便后续程序处理。

你的输出将作为后续AI任务的唯一事实来源，准确性至关重要。
        """

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_encoded_content}"
                    },
                },
            ]
        )

        # 4. 调用视觉模型进行分析
        print("--- Sending data to vision model for analysis... ---")
        analysis_response = vision_llm.invoke([message])
        print("--- Analysis complete. ---")

        return analysis_response.content

    except requests.exceptions.RequestException as e:
        error_message = f"下载媒体文件失败: {e}"
        print(f"--- [Tool Error] {error_message} ---")
        return error_message
    except Exception as e:
        error_message = f"分析媒体内容时发生未知错误: {e}"
        print(f"--- [Tool Error] {error_message} ---")
        return error_message


# 保持这个列表不变，Agent 会自动引用上面的 @tool 函数
all_tools = [get_media_content_from_url]
