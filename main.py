# main.py (DEBUGGING VERSION)

import asyncio
import warnings
import urllib.parse
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# --- astrbot 官方标准 API 导入 ---
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
import astrbot.api.message_components as Comp

# --- astrbot 插件主类 ---

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.name = "78动漫搜索插件 - 调试模式"
        self.version = "DEBUG"
        self.author = "critans & AI"

    @filter.command("78dm", "78动漫", "模型搜索", prefixes=["", "/", "#"])
    async def handle_78dm_search(self, event: AstrMessageEvent, keyword: str):
        # 参数错位修正
        the_real_event_obj = self

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!                       这 就 是 调 试 核 心                       !!
        # !!        打印出这个 event 对象的所有信息到后台控制台             !!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        logger.info("====================== DEBUGGING ASTRBOT EVENT ======================")
        logger.info(f"对象类型 (type): {type(the_real_event_obj)}")
        
        try:
            # 使用 dir() 来获取所有可用的属性和方法
            logger.info(f"可用属性 (dir): {dir(the_real_event_obj)}")
        except Exception as e:
            logger.error(f"执行 dir() 时出错: {e}")

        try:
            # 尝试获取 __dict__ 来查看实例变量
            logger.info(f"实例变量 (__dict__): {vars(the_real_event_obj)}")
        except TypeError:
            logger.warning("__dict__ 不可用，该对象可能使用了 __slots__。")
        
        logger.info("========================= DEBUGGING END =========================")

        # 在QQ里回复一条提示，告诉你去看后台
        yield the_real_event_obj.plain_result("调试信息已输出到后台控制台，请查看并复制相关日志。")
