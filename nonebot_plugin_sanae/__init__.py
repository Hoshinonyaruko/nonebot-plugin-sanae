import asyncio
import json
import atexit
import time
import aiohttp
from typing import Any
import json
import random
import configparser

from nonebot import get_driver,get_bots,on,get_bot
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import MessageSegment,Event,Message
from nonebot.adapters.onebot.v11.event import Status,Sender,Reply
from nonebot.message import  event_preprocessor
from nonebot import on_message
from nonebot.log import logger

matcher = on_message()
driver = get_driver()
sanae_config = configparser.ConfigParser()
sanae_config.read("sanae.ini")
# 创建一个字典对象保存 WebSocket 连接对象
global ws_dict
ws_dict= {}

#获取信息
on(priority=1, block=False)

@event_preprocessor
async def _(bot: Bot, event: Event):
    #把收到的信息整一整发过去
    asyncio.create_task(send_to_ws(bot.self_id,to_json(event)))

# @matcher.handle()
# async def handle_explicit_message(event: Union[GroupMessageEvent, PrivateMessageEvent]):

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Event):
            return o.__dict__
        elif isinstance(o, Message):
            return o.__dict__
        elif isinstance(o, MessageSegment):
            return o.data
        elif isinstance(o, Status):
            return o.__dict__
        elif isinstance(o, Sender):
            return o.__dict__
        elif isinstance(o, Reply):
            return o.__dict__
        else:
            return super().default(o)

def to_json(event: Event) -> str:
    return json.dumps(event, cls=CustomJSONEncoder)

@driver.on_bot_connect
async def startup():
    bots = get_bots()
    for bot_id, bot in bots.items():
        asyncio.create_task(_setup(bot_id, bot.config))

async def _setup(bot_id, config):
    async with aiohttp.ClientSession() as session:
        # 获取所有连接到 NoneBot 的 Bot 对象
        bots = get_bots()
        ws_url = generate_ws_url()
        logger.info("将连接到地址:"+ws_url)

        # 为每个 Bot 对象创建一个独立的 WebSocket 连接~
        for bot_id, bot in bots.items():
            # 设置 HTTP 头信息
            headers = {
                "User-Agent": "CQHttp/4.15.0",
                "X-Client-Role": "Universal",
                "X-Self-ID": bot_id
            }
            # 连接 WebSocket 服务端，并传递 HTTP 头信息
            try:
                async with session.ws_connect(ws_url, headers=headers) as ws:
                    # 发送连接成功的消息到 WebSocket 服务端
                    message = {
                        "meta_event_type": "lifecycle",
                        "post_type": "meta_event",
                        "self_id": bot_id,
                        "sub_type": "connect",
                        "time": int(time.time())
                    }
                    await ws.send_str(json.dumps(message))
                    # 将 WebSocket 连接对象保存到字典对象中
                    ws_dict[bot_id] = ws
                    # 开启一个新的线程来接收 WebSocket 消息~
                    async for msg in ws:
                        asyncio.create_task(recv_message(msg,bot_id))
            except aiohttp.ClientError as e:
                logger.info(f"Failed to connect websocket: {e}")
                    # 关闭 WebSocket 连接
                    #ws.close()

def generate_ws_url():
    if sanae_config.has_section("connect"):
        if not sanae_config.get("connect","ws").startswith("ws://"):
            ws_url = sanae_config.get("connect","ws").replace("http://", "ws://").replace("https://", "ws://").replace("wss://", "ws://")
            if not ws_url.startswith("ws://"):
                ws_url="ws://"+ws_url
            sanae_config.set("connect","ws",ws_url)
            with open("sanae.ini", "w") as f:
                sanae_config.write(f)  # 将修改后的配置写回文件
        return f"{sanae_config.get('connect', 'ws')}:{sanae_config.get('connect', 'port')}"
    else:
        #初次设定端口号是随机,20001~20050是早苗~
        #20001~20050,早苗
        # 20050~20070,澪
        # 20071~20099,浅羽
        # 20099-20120浅羽
        # 20120-20150澪
        port = random.randint(20001, 20150)
        #默认的早苗窝地址,交流频道,可替换为其他ob11的ws地址,https://kook.top/VAKBfJ
        ws_url = f"ws://101.35.247.237"
        if not sanae_config.has_section("connect"):
             sanae_config.add_section("connect")
        sanae_config.set("connect","ws",ws_url)
        sanae_config.set("connect","port",str(port))
        with open("sanae.ini", "w") as f:
             sanae_config.write(f)  # 将修改后的配置写回文件
        if 20001 <= port <= 20050:
            logger.info(f"Connecting to 早苗 on port {port}...答疑解惑:https://kook.top/VAKBfJ")
        elif 20050 < port <= 20070:
            logger.info(f"Connecting to 澪 on port {port}...答疑解惑:https://kook.top/gHCpJe")
        elif 20071 <= port <= 20099:
            logger.info(f"Connecting to 浅羽 on port {port}...答疑解惑:https://kook.top/ff6ZZ2")
        elif 20099 < port <= 20120:
            logger.info(f"Connecting to 浅羽 on port {port}...答疑解惑:https://kook.top/ff6ZZ2")
        else:
            logger.info(f"Connecting to 澪 on port {port}...答疑解惑:https://kook.top/gHCpJe")
        return f"{ws_url}:{port}"

async def recv_message(msg, bot_id):
    message = json.loads(msg.data)
    logger.info("收到信息 (Bot {}): {}".format(bot_id, message))
    await call_api_from_dict(bot_id, message)

async def call_api_from_dict(bot_id: str, api_request: dict) -> Any:
    """
    将请求字典转换为符合 Adapter._call_api 调用格式的参数，并调用对应的 API。

    参数:
        bot_id: 调用该 API 的 Bot ID
        api_request: API 请求的字典，格式应为 {"action": str, "params": dict}
        adapter: 用于调用 API 的 Adapter 对象

    返回:
        API 调用返回的结果
    """
    api = api_request.get("action")
    params = api_request.get("params", {})

    # 在 params 中添加 botqq 参数
    params["botqq"] = bot_id

    # 调用 Adapter._call_api
    bot=get_bot()
    return await bot.call_api(api, **params)

# 发送消息到 WebSocket 服务端
async def send_to_ws(self_id, message):
    ws_conn = ws_dict.get(self_id)
    # 如果找到对应的 WebSocket 连接对象，则发送消息
    if ws_conn:
        await ws_conn.send_str(message)

# 关闭所有 WebSocket 连接
def close_ws():
    for ws_conn in ws_dict.values():
        ws_conn.close()


# 在程序退出时关闭所有 WebSocket 连接
atexit.register(close_ws)