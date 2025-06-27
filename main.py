import asyncio
import logging
import urllib.parse
import warnings
from urllib3.exceptions import InsecureRequestWarning

import requests
from bs4 import BeautifulSoup

# --- AstrBot 核心模块导入 ---
# 确保这些导入路径与您的 AstrBot 版本匹配
from astrbot.event import MessageEvent
from astrbot.message import Message
from astrbot.plugin import Plugin

# -------------------- 爬虫辅助函数部分 --------------------

# 配置日志记录器
logger = logging.getLogger(__name__)

# 忽略requests库在https验证失败时的警告
warnings.simplefilter('ignore', InsecureRequestWarning)


def fetch_products_from_78dm(keyword: str, max_pages: int = 1):
    """
    从78dm.net抓取产品信息。
    这是一个阻塞函数，应在独立的线程中运行。
    """
    products = []
    encoded_keyword = urllib.parse.quote(keyword)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    # 为了快速响应，我们只搜索“新闻”类型(type=3)
    url = f"https://www.78dm.net/search?page=1&type=3&keyword={encoded_keyword}"
    logger.info(f"[78dm_plugin] 正在请求 URL: {url}")

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=20)
        response.raise_for_status()  # 如果请求失败 (如 404, 500), 则抛出异常

        soup = BeautifulSoup(response.text, 'html.parser')
        product_elements = soup.select('.card.is-shadowless')

        for element in product_elements:
            try:
                product_type = element.select_one('.tag-title').text.strip() if element.select_one('.tag-title') else ""
                title_div = element.select_one('.card-title')
                product_name = title_div.text.strip().replace(product_type, '').strip() if title_div else "未知名称"
                
                # 提取其他信息
                manufacturer = element.select_one('td.brand').text.strip() if element.select_one('td.brand') else "未知"
                release_date = element.select_one('td.sale-time').text.strip() if element.select_one('td.sale-time') else "未知"
                price = element.select_one('td.price\\>').text.strip() if element.select_one('td.price\\>') else "未知"
                
                product_url = ""
                link_element = element.parent
                if link_element and link_element.name == 'a' and 'href' in link_element.attrs:
                    product_url = link_element['href']
                    if product_url.startswith('//'):
                        product_url = 'https:' + product_url

                products.append({
                    'name': product_name, 'manufacturer': manufacturer,
                    'release_date': release_date, 'price': price, 'product_url': product_url
                })
            except Exception:
                # 解析单个卡片失败，记录日志并继续
                logger.warning(f"[78dm_plugin] 解析单个产品卡片时失败。", exc_info=True)
                continue
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[78dm_plugin] 网络请求失败: {e}")
        return None # 返回 None 表示网络错误
    except Exception as e:
        logger.error(f"[78dm_plugin] 抓取过程中发生未知错误: {e}")
        return None # 返回 None 表示未知错误

    return products


# -------------------- AstrBot 插件主类 --------------------

class Dm78Plugin(Plugin):
    """
    78动漫网搜索插件
    """
    # 使用 on_startswith 装饰器来匹配以 "78dm " 开头的命令。
    # 注意 "78dm" 后面的空格，这能确保我们只匹配带参数的命令，并方便地提取参数。
    @Plugin.on_startswith("78dm ")
    async def dm78_handler(self, event: MessageEvent):
        """处理 '78dm [关键词]' 命令"""
        
        # 1. 提取关键词
        # 通过切片移除命令前缀 "78dm "，然后去除首尾空格
        keyword = event.get_plaintext()[len("78dm "):].strip()

        # 2. 验证输入
        if not keyword:
            # 如果用户只输入了 "78dm " 而没有关键词，则回复用法提示
            return Message("请提供关键词！\n用法: 78dm [你要搜索的内容]")

        # 3. 发送即时反馈，提升用户体验
        try:
            await event.reply(Message(f"收到，正在为指挥官搜索“{keyword}”..."))
        except Exception as e:
            logger.warning(f"[78dm_plugin] 发送即时反馈失败: {e}")

        # 4. 在独立线程中执行耗时的网络请求，防止机器人主程序阻塞
        loop = asyncio.get_running_loop()
        try:
            # `run_in_executor` 会将阻塞函数 `fetch_products_from_78dm` 放入线程池中运行
            # `None` 表示使用默认的线程池
            products = await loop.run_in_executor(None, fetch_products_from_78dm, keyword)
        except Exception as e:
            logger.error(f"[78dm_plugin] 线程执行爬虫时发生严重错误: {e}")
            return Message(f"搜索“{keyword}”时发生内部错误，请联系管理员。")

        # 5. 根据爬虫结果，构建回复消息
        if products is None:
            return Message(f"搜索“{keyword}”时网络似乎出了点问题，请稍后再试。")

        if not products:
            return Message(f"呜... 在78动漫网没有找到关于“{keyword}”的最新资讯。")

        # 限制最多只显示前 5 条结果，防止刷屏
        results_to_show = products[:5]
        
        # 构建美观的回复文本
        response_parts = [f"为您找到关于“{keyword}”的 {len(results_to_show)} 条结果：\n--------------------"]
        for i, prod in enumerate(results_to_show, 1):
            part = (
                f"{i}. {prod.get('name')}\n"
                f"   厂商: {prod.get('manufacturer')}\n"
                f"   价格: {prod.get('price')}\n"
                f"   发售: {prod.get('release_date')}\n"
                f"   链接: {prod.get('product_url')}"
            )
            response_parts.append(part)
        response_parts.append("--------------------\n数据来源: 78dm.net")
        
        # 将所有部分用换行符合并成一个完整的消息
        response_text = "\n".join(response_parts)
        
        # 返回最终的 Message 对象，AstrBot 会自动发送到消息来源地
        return Message(response_text)
