from wechatpy.enterprise import WeChatClient, events
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.events import register_event
from wechatpy.events import BaseEvent
from wechatpy.fields import StringField

import config

# 1. 初始化企业微信 API 客户端
# wechatpy 会自动处理 access_token 的获取和刷新
client = WeChatClient(
    corp_id=config.WECOM_CORP_ID,
    secret=config.WECOM_SECRET,
    # access_token 会被自动缓存
)

# 2. 初始化加解密处理器
crypto = WeChatCrypto(
    token=config.WECOM_TOKEN,
    encoding_aes_key=config.WECOM_ENCODING_AES_KEY,
    corp_id=config.WECOM_CORP_ID
)

def get_media_url(media_id: str) -> str:
    """
    根据 media_id 获取临时素材的 URL。
    注意：这是临时 URL，有访问时效和权限限制。Agent 直接访问可能失败。
    更稳妥的方式是服务器先下载，再提供给多模态模型。
    这里为了逻辑对齐 n8n 工作流，先拼接 URL。
    """
    access_token = client.access_token
    return f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"


def sync_kf_messages(open_kfid: str, token: str) -> list:
    """
    调用企业微信客服消息同步接口，获取最近5条的聊天记录。

    :param open_kfid: 客服帐号ID
    :param token: 回调事件中携带的 'Token'，用于定位消息位置
    :return: 消息列表，如果失败则返回空列表
    """
    if not token:
        print("Sync kf messages call ignored due to empty token.")
        return []

    try:
        print(f"Syncing messages for open_kfid: {open_kfid}")
        # wechatpy 的 client.post 会自动处理 access_token
        response = client.post(
            "kf/sync_msg",
            data={
                "open_kfid": open_kfid,
                "token": token
            }
        )
        # wechatpy 会在 API 返回错误码时自动抛出异常，所以这里无需检查 errcode
        msg_list = response.get("msg_list", [])
        print(f"Successfully synced {len(msg_list)} messages.")
        # print(f"msg_list: {msg_list}")
        latest_msg_list = []
        for msg in reversed(msg_list):
            latest_msg_list.append(msg)
            if msg['msgtype'] == 'event':
                if msg['event']['event_type'] == 'enter_session':
                    break
        return latest_msg_list[:5][::-1]
    except Exception as e:
        print(f"Failed to sync kf messages: {e}")
        return []

def send_kf_message(open_kfid: str, touser: str, msg_content: str):
    """
    发送客服消息。

    :param open_kfid: 客服帐号ID
    :param touser: 接收消息的成员ID
    :param msg_content: 消息内容
    :return: 发送结果
    """
    response = client.post(
        "kf/send_msg",
        data={
            "open_kfid": open_kfid,
            "touser": touser,
            "msgtype": "text",
            "text": {
                "content": msg_content
            }
        }
    )
    print(f"Sent kf message: {response}")

@register_event('kf_msg_or_event')
class KfMsgOrEvent(BaseEvent):
    """
    客服消息或事件
    详情请参阅
    https://qydev.weixin.qq.com/wiki/index.php?title=接收事件#.E6.88.90.E5.91.98.E5.85.B3.E6.B3.A8.2F.E5.8F.96.E6.B6.88.E5.85.B3.E6.B3.A8.E4.BA.8B.E4.BB.B6
    """
    event = 'kf_msg_or_event'
    token = StringField('Token')
    open_kf_id = StringField('OpenKfId')

