from .main import S78DmPlugin

class PluginLoad:
    """
    插件加载类
    """
    name = "78dm.net Search"
    usage = "命令: 78search [关键词]\n功能: 在78动漫模型网搜索模玩信息并返回结果。"
    plugin = S78DmPlugin
