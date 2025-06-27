import asyncio
import logging
import urllib.parse
import warnings
from urllib3.exceptions import InsecureRequestWarning

import requests
from bs4 import BeautifulSoup

from astrbot.event import MessageEvent
from astrbot.message import Message
from astrbot.plugin import Plugin

# --- 爬虫代码部分 ---

# 配置日志
logger = logging.getLogger(__name__)

# 忽略SSL警告
warnings.simplefilter('ignore', InsecureRequestWarning)


def extract_product_info_from_html(product_element):
    """从HTML产品元素中提取信息"""
    try:
        product_type = product_element.select_one('.tag-title').text.strip() if product_element.select_one('.tag-title') else "未知类型"
        title_div = product_element.select_one('.card-title')
        product_name = title_div.text.strip().replace(product_type, '').strip() if title_div else "未知名称"
        manufacturer = product_element.select_one('td.brand').text.strip() if product_element.select_one('td.brand') else "未知厂商"
        release_date = product_element.select_one('td.sale-time').text.strip() if product_element.select_one('td.sale-time') else "未知发售"
        price = product_element.select_one('td.price\\>').text.strip() if product_element.select_one('td.price\\>') else "未知价格"
        
        image_url = ""
        img_element = product_element.select_one('img.single-cover')
        if img_element and 'src' in img_element.attrs:
            image_url = img_element['src']
            
        product_url = ""
        link_element = product_element.parent
        if link_element and link_element.name == 'a' and 'href' in link_element.attrs:
            product_url = link_element['href']
            if product_url.startswith('//'):
                product_url = 'https:' + product_url
        
        return {
            'type': product_type, 'name': product_name, 'manufacturer': manufacturer,
            'release_date': release_date, 'price': price, 'image_url': image_url, 'product_url': product_url
        }
    except Exception as e:
        logger.error(f"提取产品信息时出错: {e}")
        return None

def fetch_products_api(keyword, search_type=3, max_pages=1):
    """使用API接口获取产品信息 (为机器人优化，默认只爬1页)"""
    products = []
    encoded_keyword = urllib.parse.quote(keyword)
    
    headers = {
        "accept": "*/*", "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for page in range(1, max_pages + 1):
        url = f"https://www.78dm.net/search?page={page}&type={search_type}&keyword={encoded_keyword}"
        logger.info(f"插件正在请求: {url}")
        
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=15)
            if response.status_code != 200:
                logger.warning(f"API请求失败，状态码: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            if search_type == 3:
                product_elements = soup.select('.card.is-shadowless')
                if not product_elements:
                    logger.info("未找到新闻元素，搜索结束")
                    break
                for element in product_elements:
                    info = extract_product_info_from_html(element)
                    if info:
                        products.append(info)
            # 可以根据需要添加对 search_type == 1 (单品) 的支持
            
        except Exception as e:
            logger.error(f"获取第{page}页数据时出错: {e}")
            break
            
    return products

# --- AstrBot 插件类 ---

class S78DmPlugin(Plugin):
    """
    78dm.net 搜索插件
    """
    @Plugin.on_startswith("78search")
    async def search_handler(self, event: MessageEvent):
        # 1. 解析用户输入的关键词
        keyword = event.get_plaintext().replace("78search", "").strip()
        
        if not keyword:
            return Message("指令格式错误喵~\n请使用: 78search [关键词]\n例如: 78search 高达")

        # 2. 发送一个 "正在搜索" 的提示，提升用户体验
        try:
            await event.reply(Message(f"收到！正在为指挥官搜索“{keyword}”的相关信息..."))
        except Exception as e:
            logger.warning(f"发送'正在搜索'提示时失败: {e}")

        # 3. 在独立的线程中运行耗时的爬虫函数，避免阻塞
        try:
            # 使用 asyncio.to_thread 在 Python 3.9+ 中更现代
            # 为了兼容性，这里可以使用 loop.run_in_executor
            loop = asyncio.get_running_loop()
            # 为了快速响应，我们只搜索新闻(type=3)的第一页(max_pages=1)
            products = await loop.run_in_executor(
                None, fetch_products_api, keyword, 3, 1
            )
        except Exception as e:
            logger.error(f"执行爬虫时发生严重错误: {e}")
            return Message(f"搜索“{keyword}”时发生内部错误，请稍后再试或联系管理员。")

        # 4. 根据爬虫结果，格式化并返回消息
        if not products:
            return Message(f"呜...没有找到关于“{keyword}”的任何信息。\n请试试更换关键词哦。")

        # 限制最多只显示前 5 条结果，防止刷屏
        results_to_show = products[:5]
        
        # 构建回复消息
        response_text = f"为指挥官找到了关于“{keyword}”的 {len(results_to_show)} 条结果：\n"
        response_text += "--------------------\n"
        
        for i, prod in enumerate(results_to_show, 1):
            response_text += (
                f"{i}. {prod.get('name', '未知名称')}\n"
                f"   厂商: {prod.get('manufacturer', '未知')}\n"
                f"   价格: {prod.get('price', '未知')}\n"
                f"   发售: {prod.get('release_date', '未知')}\n"
                f"   链接: {prod.get('product_url', '无')}\n"
                f"--------------------\n"
            )
        
        response_text += f"数据来源: 78dm.net"
        
        return Message(response_text)
