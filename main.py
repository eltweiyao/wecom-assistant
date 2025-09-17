import asyncio
import json
import time
import uuid
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from wechatpy.enterprise import parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.utils import to_text

import config
from agent import invoke_agent
from wecom_handler import crypto, client, get_media_url, sync_kf_messages, send_kf_message
from exceptions import (
    WecomAssistantException, WecomException, LLMException, ToolException,
    ErrorCode, handle_exception, error_reporter
)
from logging_config import logger
from monitoring import performance_monitor, health_checker, get_performance_report

app = FastAPI(title="企业微信智能助手", version="1.0.0")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    health_results = health_checker.run_all_checks()
    overall_status = health_checker.get_overall_status()
    
    status_code = 200
    if overall_status == "unhealthy":
        status_code = 503
    elif overall_status == "warning":
        status_code = 200  # 警告状态仍返回200，但在响应中标明
    
    return Response(
        content=json.dumps({
            "status": overall_status,
            "checks": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "response_time": result.response_time
                }
                for name, result in health_results.items()
            }
        }, ensure_ascii=False, indent=2),
        status_code=status_code,
        media_type="application/json"
    )


@app.get("/metrics")
async def get_metrics():
    """获取性能指标"""
    report = get_performance_report()
    return Response(
        content=json.dumps(report, ensure_ascii=False, indent=2),
        media_type="application/json"
    )


def extract_content(msg, output_contents: List[str], sender_name: Optional[str] = None):

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
        output_contents.append(f"{user_id} 发送了一条消息，content是: 你好！")
    elif msg['msgtype'] == 'merged_msg':
        merged_msg_list = msg['merged_msg']['item']
        [extract_content(json.loads(item['msg_content']), output_contents, item['sender_name']) for item in merged_msg_list]


def process_messages(user_input: list, user_id: str, agent_id: str, open_kfid: str, request_id: str):
    """
    这个函数在后台运行，处理所有耗时操作。
    """
    start_time = time.time()
    success = False
    
    # 增加活跃请求计数
    performance_monitor.increment_active_requests()
    
    try:
        logger.log_request_start(user_id, "background_processing", request_id)
        logger.debug(
            "Background task started",
            user_id=user_id,
            request_id=request_id,
            input_length=len(str(user_input))
        )

        # 调用 Agent 获取智能回复 (这是主要耗时操作)
        agent_response = invoke_agent(user_input, request_id)
        
        logger.debug(
            "Agent response received",
            user_id=user_id,
            request_id=request_id,
            response_length=len(agent_response)
        )
        
        # 将消息返回给用户
        if open_kfid:
            send_kf_message(open_kfid, user_id, agent_response)
        else:
            client.message.send_text(agent_id, user_id, agent_response)
        
        success = True
        execution_time = time.time() - start_time
        logger.log_request_end(user_id, request_id, execution_time, success=True)
        
    except Exception as e:
        execution_time = time.time() - start_time
        wrapped_exception = handle_exception(e, "background_message_processing", user_id)
        
        logger.log_exception(
            wrapped_exception,
            context="background_message_processing",
            user_id=user_id,
            request_id=request_id,
            execution_time=execution_time
        )
        
        error_reporter.report_error(wrapped_exception)
        
        # 发送用户友好的错误消息
        try:
            error_message = wrapped_exception.user_message
            if open_kfid:
                send_kf_message(open_kfid, user_id, error_message)
            else:
                client.message.send_text(agent_id, user_id, error_message)
        except Exception as send_error:
            logger.error(
                "Failed to send error message to user",
                user_id=user_id,
                request_id=request_id,
                send_error=str(send_error)
            )
        
        execution_time = time.time() - start_time
        logger.log_request_end(user_id, request_id, execution_time, success=False)
    
    finally:
        # 减少活跃请求计数并记录性能指标
        performance_monitor.decrement_active_requests()
        execution_time = time.time() - start_time
        performance_monitor.record_request(success, execution_time)


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
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    signature = request.query_params.get("msg_signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")
    
    logger.debug(
        "WeChat callback received",
        request_id=request_id,
        method=request.method,
        signature_provided=bool(signature)
    )

    if request.method == "GET":
        # --- URL 验证逻辑 ---
        echostr = request.query_params.get("echostr", "")
        try:
            echostr = crypto.check_signature(signature, timestamp, nonce, echostr)
            logger.info(
                "WeChat server verification successful",
                request_id=request_id,
                event="server_verification_success"
            )
            return Response(content=to_text(echostr), status_code=200)
        except InvalidSignatureException as e:
            logger.warning(
                "WeChat server verification failed",
                request_id=request_id,
                error=str(e),
                event="server_verification_failed"
            )
            return Response(content="Invalid signature", status_code=401)

    elif request.method == "POST":
        # --- 消息接收和处理逻辑 ---
        body = await request.body()
        try:
            # 解密消息
            decrypted_message = crypto.decrypt_message(body, signature, timestamp, nonce)
            logger.debug(
                "Message decrypted successfully",
                request_id=request_id,
                message_length=len(decrypted_message)
            )
            
            # 解析 XML 消息为 wechatpy 的消息对象
            msg = parse_message(decrypted_message)
            if not msg:
                logger.warning("Failed to parse message", request_id=request_id)
                return Response(status_code=400)
            
            open_kf_id = getattr(msg, 'open_kf_id', None)
            user_id = msg.source
            
            logger.log_wecom_event(
                event_type=msg.type,
                user_id=user_id,
                details={
                    "open_kf_id": open_kf_id,
                    "request_id": request_id
                }
            )
            # 异步处理消息
            user_input_contents = []
            if msg.type == 'event':
                # 客服场景下的事件，通常带有 open_kf_id 和 token
                token = getattr(msg, 'token', None)
                # 只有带 token 的事件才处理，这通常是用户进入会话等需要拉取上下文的事件
                if token and open_kf_id:
                    # 1. 同步消息
                    msg_list = sync_kf_messages(open_kf_id, token)
                    user_id = msg_list[-1]['external_userid']
                    # 获取最新的会话消息

                    # 2. 格式化历史消息为 LLM 的输入 当前默认只取最新一条
                    [extract_content(msg, user_input_contents) for msg in msg_list[-1:]]
                else:
                    # 如果是没有 token 的事件，直接忽略，不处理
                    logger.debug(
                        "Event ignored due to missing token",
                        user_id=user_id,
                        request_id=request_id,
                        event_type=getattr(msg, 'event', 'unknown')
                    )
                    return Response(status_code=200)
            elif msg.type == 'text':
                user_input_contents.append(f"{user_id} 发送了一条消息，content是: {msg.content}")
            elif msg.type in ['image', 'video', 'voice', 'file']:
                user_input_contents.append(f"{user_id} 发送了一个{msg.type}，URL是: {get_media_url(msg.media_id)}")
            else:
                # 其他类型的消息暂不处理，直接回复
                logger.warning(
                    "Unsupported message type",
                    user_id=user_id,
                    request_id=request_id,
                    message_type=msg.type
                )
                client.message.send_text(config.WECOM_AGENT_ID, user_id, "我暂时无法处理这种类型的消息。")
                return Response(status_code=200)

            # 异步处理消息
            background_tasks.add_task(
                process_messages, 
                user_input_contents, 
                user_id, 
                config.WECOM_AGENT_ID, 
                open_kf_id or "",  # 保证不传入None
                request_id
            )

            # 立即返回 200 OK 响应给企业微信服务器
            logger.info(
                "Message queued for background processing",
                user_id=user_id,
                request_id=request_id,
                response_time=time.time() - start_time
            )
            return Response(status_code=200)

        except InvalidSignatureException as e:
            logger.warning(
                "Message signature verification failed",
                request_id=request_id,
                error=str(e)
            )
            return Response(content="Invalid signature", status_code=401)
        except Exception as e:
            wrapped_exception = handle_exception(e, "wechat_callback", None)
            error_reporter.report_error(wrapped_exception)
            
            logger.log_exception(
                wrapped_exception,
                context="wechat_callback",
                request_id=request_id
            )
            
            return Response(status_code=500)
    return None


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # user_input_contents = []
    # msg_list = sync_kf_messages('wk54emFgAAzu4SxidhEK4Fk5MRPQygTw', 'ENC9xiGTgQZ2XqHH3oAvKwpxT8iQZYvUYjmjEbkphmTxDNS')
    # user_id = msg_list[-1]['external_userid']
    # 获取最新的会话消息
    #
    # 2. 格式化历史消息为 LLM 的输入 当前默认只取最新一条
    # [extract_content(msg, user_input_contents) for msg in msg_list[-1:]]
    # print(user_input_contents)
    # agent_response = invoke_agent(["我拉着一车小脑袋鱼过高速收费站时，被工作人员说这不是绿通商品，不能享受政策，这怎么办"])
