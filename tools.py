import base64

import pdfplumber
import requests
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import config
import rag

# 初始化一个专门用于视觉分析的 LLM 客户端
# 我们在这里单独初始化，因为它使用了与主 Agent 不同的模型
try:
    vision_llm = ChatOpenAI(
        model=config.VISION_MODEL_NAME,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_API_BASE,
        temperature=0,  # 视觉分析任务通常需要更确定的结果
    )
    green_channel_llm = ChatOpenAI(
        model=config.LLM_MODEL_NAME,
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


@tool
def highway_knowledge_retriever(query: str) -> str:
    """
    当用户询问关于高速公路的规定、政策、收费、应急处理等专业知识时，使用此工具来获取相关的原始知识文档。
    此工具会返回最相关的知识片段，而不是直接的答案。
    """
    # 步骤 a: 调用retriever获取相关文档
    retrieved_docs = rag.retriever.invoke(query)

    print(f"--- Retrieved {len(retrieved_docs)} documents for query: {query} ---")
    print(f"--- Retrieved documents: {retrieved_docs} ---")
    if not retrieved_docs:
        return "知识库中没有找到相关信息。"

    # 步骤 b: 从文档中提取原始上下文并格式化
    # 注意：这里我们返回metadata中的'answer'，因为我们之前的数据结构是这样设计的。
    # 这完全没问题，这里的“原始上下文”就是指我们存放在answer里的标准答案文本。
    context = "\n\n".join(doc.metadata['answer'] for doc in retrieved_docs)

    return context


# 解析绿通货物及其别名名单
def read_green_channel_goods(path: str) -> list:
    goods = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row[0] != "类别":
                        goods.append(row[1])
                        goods.extend(row[2].replace("\n", "").split("、"))
    return goods


green_channel_goods = read_green_channel_goods("data/P020230119517474576854.pdf")
green_channel_goods.extend(read_green_channel_goods("data/P020230119517474781161.pdf"))

green_channel_categories = [
    "鱼类",
    "虾类",
    "贝类",
    "蟹类",
    "海带",
    "紫菜",
    "海蜇",
    "海参",
    "仔猪",
    "蜜蜂",
    "新鲜家禽肉和家畜肉",
    "新鲜的蛋类",
    "生鲜乳"]

@tool
def check_green_channel_status(item_name: str) -> bool:
    """
    一个能处理别名的智能工具，用于检查货物是否在绿通名单上。
    """
    is_on_list = item_name in green_channel_goods
    print(f"查询: '{item_name}' -> 结果: {is_on_list}")
    if not is_on_list:
        prompt_text = f"""
        请将以下物品归入最合适的类别中。
        可选的类别有：{green_channel_categories}

        物品："{item_name}"

        请只回答一个类别名称，如果有你不认识的物品无法归类，请回答“未知”，不要包含任何解释或多余的文字。。
        """
        print("--- Sending data to llm for category... ---")
        category = green_channel_llm.invoke([prompt_text])
        print(f"--- Category identified: {category} ---")
        is_on_list = category in green_channel_categories
        print(f"查询: '{item_name}' -> 识别类别: '{category}' -> 识别结果: {is_on_list}")

    return is_on_list


# 保持这个列表不变，Agent 会自动引用上面的 @tool 函数
all_tools = [get_media_content_from_url, highway_knowledge_retriever, check_green_channel_status]
