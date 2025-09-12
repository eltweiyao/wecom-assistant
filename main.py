import asyncio
import json

import uvicorn
from fastapi import FastAPI, Request, Response, BackgroundTasks
from wechatpy.enterprise import parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import to_text

import config
from agent import invoke_agent
from wecom_handler import crypto, client, get_media_url, sync_kf_messages, send_kf_message

app = FastAPI()


def extract_content(msg, output_contents: list, sender_name: str = None):

    user_id = sender_name or msg.get('sender_name') or msg.get('external_userid')
    if msg['msgtype'] == 'text':
        output_contents.append(f"{user_id} 发送了一条消息，content是: {msg['text']['content']}")
    elif msg['msgtype'] in ['image', 'video', 'voice', 'file']:
        # 获取媒体文件的临时 URL
        media_id = msg.get(msg['msgtype']).get('media_id')
        media_url = get_media_url(media_id)
        # 格式化输入，让 Agent 知道这是一个媒体文件
        output_contents.append(f"{user_id} 发送了一个{msg['msgtype']}，URL是: {media_url}")
        print(f"--- Generated Media URL: {media_url} ---")
    elif msg['msgtype'] == 'event' and msg['event']['event_type'] == 'enter_session':
        user_id = msg['event']['external_userid']
        output_contents.append(f"{user_id} 进入会话")
    elif msg['msgtype'] == 'merged_msg':
        merged_msg_list = msg['merged_msg']['item']
        [extract_content(json.loads(item['msg_content']), output_contents, item['sender_name']) for item in merged_msg_list]


async def process_messages(user_input: list, user_id: str, agent_id: str, open_kfid: str):
    """
    这个函数在后台运行，处理所有耗时操作。
    """
    try:
        print(f"--- [Background Task] Started for user: {user_id} ---")
        print(f"--- [Background Task] Input: {user_input}... ---")  # 日志截断，避免过长

        # 调用 Agent 获取智能回复 (这是主要耗时操作)
        agent_response = await invoke_agent(user_input)
        print(f"--- [Background Task] Agent Response: {agent_response} ---")
        # 将消息返回给 用户
        if open_kfid:
            send_kf_message(open_kfid, user_id, agent_response)
        else:
            client.message.send_text(agent_id, user_id, agent_response)
        print(f"--- [Background Task] Sent response to user: {user_id} ---")
    except Exception as e:
        # 在后台任务中也进行异常处理，避免后台任务崩溃
        print(f"--- [Background Task Error] An error occurred: {e} ---")
        # 可以考虑在这里发送一条错误提示给用户
        client.message.send_text(agent_id, user_id, "抱歉，处理你的消息时遇到了内部错误。")


@app.api_route(
    "/wechat-agent-callback",  # 定义你的回调路径
    methods=["GET", "POST"],
    summary="企业微信应用回调接口"
)
async def wechat_callback(request: Request, background_tasks: BackgroundTasks):
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
            print(f"--- [decrypted_message]: {decrypted_message} ---")
            # 解析 XML 消息为 wechatpy 的消息对象
            msg = parse_message(decrypted_message)
            print(f"--- [Received Message] Type: {msg.type}，Msg:{msg} ---")
            open_kf_id = getattr(msg, 'open_kf_id', None)
            user_id = msg.source
            # 异步处理消息
            user_input_contents = []
            if msg.type == 'event':
                # 客服场景下的事件，通常带有 open_kf_id 和 token
                token = getattr(msg, 'token', None)
                # 只有带 token 的事件才处理，这通常是用户进入会话等需要拉取上下文的事件
                if token:
                    # 1. 同步消息
                    msg_list = sync_kf_messages(open_kf_id, token)
                    user_id = msg_list[-1]['external_userid']
                    # 获取最新的会话消息

                    # 2. 格式化历史消息为 LLM 的输入 当前默认只取最新一条
                    [extract_content(msg, user_input_contents) for msg in msg_list[:1]]
                else:
                    # 如果是没有 token 的事件，直接忽略，不处理
                    print(f"--- [Event] Ignored event of type '{getattr(msg, 'event', 'unknown')}' with no token. ---")
                    return Response(status_code=200)
            elif msg.type == 'text':
                user_input_contents.append(f"{user_id} 发送了一条消息，content是: {msg.content}")
            elif msg.type in ['image', 'video', 'voice', 'file']:
                user_input_contents.append(f"{user_id} 发送了一个{msg.type}，URL是: {get_media_url(msg.media_id)}")
            else:
                # 其他类型的消息暂不处理，直接回复
                client.message.send_text(config.WECOM_AGENT_ID, user_id, "我暂时无法处理这种类型的消息。")
                return Response(status_code=200)

            # 异步处理消息
            background_tasks.add_task(process_messages, user_input_contents, user_id, config.WECOM_AGENT_ID, open_kf_id)

            # 立即返回 200 OK 响应给企业微信服务器
            print(f"--- [Immediate Response] Sent 200 OK for user: {user_id}. Task queued. ---")
            return Response(status_code=200)

        except InvalidSignatureException:
            print("消息签名验证失败！")
            return Response(content="Invalid signature", status_code=401)
        except Exception as e:
            print(f"处理消息时发生错误: {e}")
            return Response(status_code=500)
    return None


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # latest_msg_list = sync_kf_messages('wk54emFgAAzu4SxidhEK4Fk5MRPQygTw', 'ENCFiHvZGBiGSvCo6T1h8soJkERuUupXoSqhVEpB4MWBA1j')
    # output_lines = []
    # [extract_content(msg, output_lines) for msg in latest_msg_list]
    # print(output_lines)

# 你可以先独立测试RAG链
# if __name__ == '__main__':
#     question = "我在高速车坏了怎么办"
#     asyncio.run(invoke_agent([{"input": question}]))