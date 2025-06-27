
#### 3. 插件入口 `__init__.py`
# 从 main.py 文件中导入的插件主类
from .main import Dm78Plugin

class PluginLoad:
    """
    插件加载类，AstrBot 会读取这个类来加载插件。
    """
    # 插件的名称，应与 metadata.yaml 中的 name 一致
    name = "78animeSearch"
    # 插件的用法说明，会在帮助命令中显示
    usage = "命令: 78dm [关键词]\n功能: 在78动漫模型网搜索最新的资讯和模型信息。"
    # 指向你的插件主类
    plugin = Dm78Plugin
    # 插件加载的优先级，默认为0，无需修改
    priority = 0
