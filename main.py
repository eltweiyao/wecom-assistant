import asyncio

import uvicorn
from fastapi import FastAPI, Request, Response
from wechatpy.enterprise import parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import to_text

import config
from wecom_handler import crypto, client, get_media_url
from agent import invoke_agent

app = FastAPI()


@app.api_route(
    "/wechat-agent-callback",  # 定义你的回调路径
    methods=["GET", "POST"],
    summary="企业微信应用回调接口"
)
async def wechat_callback(request: Request):
    """
    处理企业微信回调：
    - GET: 用于服务器配置验证
    - POST: 用于接收用户消息
    """
    signature = request.query_params.get("msg_signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")

    if request.method == "GET":
        # --- URL 验证逻辑 ---
        echostr = request.query_params.get("echostr", "")
        try:
            echostr = crypto.check_signature(signature, timestamp, nonce, echostr)
            print("企业微信服务器配置验证成功！")
            return Response(content=to_text(echostr), status_code=200)
        except InvalidSignatureException:
            print("企业微信服务器配置验证失败！")
            return Response(content="Invalid signature", status_code=401)

    elif request.method == "POST":
        # --- 消息接收和处理逻辑 ---
        body = await request.body()
        try:
            # 解密消息
            decrypted_message = crypto.decrypt_message(body, signature, timestamp, nonce)
            # 解析 XML 消息为 wechatpy 的消息对象
            msg = parse_message(decrypted_message)
            print(f"--- [Received Message] Type: {msg.type}, User: {msg.source} ---")
            #异步处理消息
            asyncio.run(process_wecom_message(msg))
            # 必须返回 200 OK，否则企业微信会重试
            return Response(status_code=200)

        except InvalidSignatureException:
            print("消息签名验证失败！")
            return Response(content="Invalid signature", status_code=401)
        except Exception as e:
            print(f"处理消息时发生错误: {e}")
            return Response(status_code=500)
    return None

async def process_wecom_message(msg):
    if msg.type == 'text':
        user_input = f"用户发送了一条消息，content是: {msg.content}"
    elif msg.type in ['image', 'video', 'voice', 'file']:
        # 获取媒体文件的临时 URL
        media_id = msg.media_id
        media_url = get_media_url(media_id)
        # 格式化输入，让 Agent 知道这是一个媒体文件
        user_input = f"用户发送了一个{msg.type}，URL是: {media_url}"
        print(f"--- Generated Media URL: {media_url} ---")
    else:
        # 其他类型的消息暂不处理，直接回复
        client.message.send_text(config.WECOM_AGENT_ID, msg.source, "我暂时无法处理这种类型的消息。")
        return Response(status_code=200)

    # 调用 Agent 获取智能回复
    agent_response = await invoke_agent(user_input)

    print(f"--- [Agent Response]: {agent_response} ---")

    # 将 Agent 的回复发送给用户
    client.message.send_text(config.WECOM_AGENT_ID, msg.source, agent_response)
    return None


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
