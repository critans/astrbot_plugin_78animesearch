import asyncio
import logging
import urllib.parse
import warnings
from urllib3.exceptions import InsecureRequestWarning

import requests
from bs4 import BeautifulSoup

# --- 导入最新的 AstrBot API ---
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger  # 使用 astrbot 提供的 logger 接口

# -------------------- 爬虫辅助函数部分 (保持不变) --------------------

warnings.simplefilter('ignore', InsecureRequestWarning)

def fetch_products_from_78dm(keyword: str):
    """从78dm.net抓取产品信息 (阻塞函数)"""
    products = []
    encoded_keyword = urllib.parse.quote(keyword)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://www.78dm.net/search?page=1&type=3&keyword={encoded_keyword}"
    logger.info(f"[78dm_plugin] 正在请求 URL: {url}")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        product_elements = soup.select('.card.is-shadowless')
        for element in product_elements:
            try:
                product_type = element.select_one('.tag-title').text.strip() if element.select_one('.tag-title') else ""
                title_div = element.select_one('.card-title')
                product_name = title_div.text.strip().replace(product_type, '').strip() if title_div else "未知名称"
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
                logger.warning(f"[78dm_plugin] 解析单个产品卡片时失败。", exc_info=True)
                continue
    except Exception as e:
        logger.error(f"[78dm_plugin] 抓取过程中发生错误: {e}")
        return None
    return products

# -------------------- AstrBot 插件主类 (全新API风格) --------------------

# 使用 @register 装饰器直接注册插件，取代了旧的 PluginLoad 方式
@register(
    "78dm_search",
    author="critans & AI",
    version="2.0.0",
    description="通过 '78dm [关键词]' 命令在 78dm.net 搜索模玩信息。"
)
class Dm78Plugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 可以在这里进行一些初始化操作

    # 使用 @filter.command 装饰器注册命令
    # astrbot 会自动处理命令和参数的分割
    @filter.command("78dm")
    async def dm78_handler(self, event: AstrMessageEvent):
        """响应 '78dm' 命令，搜索78动漫网。"""
        
        # 1. 提取参数
        # 新的 API 会将命令后的内容作为参数，我们可以直接从 event 中获取
        keyword = event.get_command_args()

        # 2. 验证输入
        if not keyword:
            yield event.plain_result("请提供关键词！\n用法: 78dm [你要搜索的内容]")
            return

        # 3. 在独立线程中执行耗时的网络请求
        loop = asyncio.get_running_loop()
        try:
            # yield 一个即时反馈，提升用户体验
            yield event.plain_result(f"收到，正在为指挥官搜索“{keyword}”...")
            
            products = await loop.run_in_executor(None, fetch_products_from_78dm, keyword)
        except Exception as e:
            logger.error(f"[78dm_plugin] 线程执行爬虫时发生严重错误: {e}")
            yield event.plain_result(f"搜索“{keyword}”时发生内部错误，请联系管理员。")
            return

        # 4. 根据爬虫结果，构建最终回复
        if products is None:
            yield event.plain_result(f"搜索“{keyword}”时网络似乎出了点问题，请稍后再试。")
            return

        if not products:
            yield event.plain_result(f"呜... 在78动漫网没有找到关于“{keyword}”的最新资讯。")
            return

        # 5. 格式化输出
        results_to_show = products[:5]
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
        
        final_response = "\n".join(response_parts)
        
        # 6. 使用 yield event.plain_result() 发送最终结果
        yield event.plain_result(final_response)

    async def terminate(self):
        """插件被卸载或停用时调用，可选。"""
        pass
