import asyncio
import logging

# 导入 AstrBot 核心模块
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# # 注册一个临时的调试插件
# @register(
#     "78dm_search_debugger",
#     "critans & AI",
#     "一个用于诊断 context 对象的调试工具。",
#     "9.9.9-debug"
# )
class Dm78PluginDebugger(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("--- [78DM DEBUGGER] Plugin Initialized ---")

    @filter.command("78dm")
    async def dm78_debug_handler(self, context: Context):
        """
        这是一个特殊的调试处理函数。
        它的唯一作用就是将接收到的 context 对象的所有信息打印到日志中。
        """
        logger.info("!!!!!!!!!! 78DM DEBUGGER TRIGGERED !!!!!!!!!!")
        try:
            # 打印接收到的对象的类型
            logger.info(f"Handler received an object of type: {type(context)}")
            
            # 打印该对象的所有可用属性和方法
            logger.info("--- Attributes of the received context object: ---")
            attributes = dir(context)
            for attr in attributes:
                logger.info(f"-> {attr}")
            logger.info("--- End of Attributes ---")

            # 尝试打印一些可能存在的属性的值
            if 'event' in attributes:
                 logger.info(f"Value of context.event: {getattr(context, 'event')}")
            if 'message' in attributes:
                 logger.info(f"Value of context.message: {getattr(context, 'message')}")
            if 'msg' in attributes:
                 logger.info(f"Value of context.msg: {getattr(context, 'msg')}")


        except Exception as e:
            logger.error(f"An error occurred during object inspection: {e}", exc_info=True)
        
        logger.info("!!!!!!!!!! DEBUGGING COMPLETE, NO REPLY SENT !!!!!!!!!!")
        
        # 这是一个异步生成器，但我们不产生任何值，以便安全退出。
        if False:
            yield
