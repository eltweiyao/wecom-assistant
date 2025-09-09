from wechatpy.enterprise import WeChatClient
from wechatpy.enterprise.crypto import WeChatCrypto
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