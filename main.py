# main.py

import asyncio
import warnings
import urllib.parse
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# --- astrbot 官方标准 API 导入 ---
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp


# --- 爬虫代码部分 ---
warnings.simplefilter('ignore', InsecureRequestWarning)

def extract_product_info_from_html(product_element):
    """从HTML产品元素中提取信息"""
    try:
        product_type = product_element.select_one('.tag-title').text.strip() if product_element.select_one('.tag-title') else "未知类型"
        title_div = product_element.select_one('.card-title')
        title_text = title_div.text.strip() if title_div else "未知名称"
        product_name = title_text.replace(product_type, '').strip() if product_type in title_text else title_text
        manufacturer = product_element.select_one('td.brand').text.strip() if product_element.select_one('td.brand') else "未知厂商"
        release_date = product_element.select_one('td.sale-time').text.strip() if product_element.select_one('td.sale-time') else "未知发售"
        price = product_element.select_one('td.price\\>').text.strip() if product_element.select_one('td.price\\>') else "未知价格"
        
        image_url = ""
        img_element = product_element.select_one('img.single-cover')
        if img_element and 'src' in img_element.attrs:
            src = img_element['src']
            if src.startswith('//'):
                image_url = 'https:' + src
            elif src.startswith('/'):
                image_url = 'https://www.78dm.net' + src
            else:
                image_url = src
        
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
        logger.error(f"[78animeSearch] 提取产品信息时出错: {e}")
        return None

def fetch_products_from_78dm(keyword: str, max_pages: int = 1):
    """
    爬取78dm.net的商品信息 (同步版本，用于在异步函数中调用)
    """
    products = []
    encoded_keyword = urllib.parse.quote(keyword)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for page in range(1, max_pages + 1):
        url = f"https://www.78dm.net/search?page={page}&type=3&keyword={encoded_keyword}"
        logger.info(f"[78animeSearch] 正在爬取页面: {url}")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=20)
            if response.status_code != 200:
                logger.warning(f"[78animeSearch] 请求失败，状态码: {response.status_code} for URL: {url}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            product_elements = soup.select('.card.is-shadowless')

            if not product_elements:
                logger.info(f"[78animeSearch] 第{page}页没有找到产品元素，停止爬取。")
                break
            
            for element in product_elements:
                product_info = extract_product_info_from_html(element)
                if product_info:
                    products.append(product_info)
            
        except Exception as e:
            logger.error(f"[78animeSearch] 爬取第{page}页数据时出错: {e}")
            break
            
    return products

# --- astrbot 插件主类 ---

@register(
    "78animeSearch",
    "critans",
    "通过 '78dm [关键词]' 命令在78动漫模型网搜索信息。",
    "v2.0",
    "https://github.com/critans/astrbot_plugin_78animesearch"
)

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.name = "78动漫搜索插件"
        self.version = "2.0"
        self.author = "critans"

    @filter.command("78dm", prefixes=["", "/", "#"])
    async def handle_78dm_search(self, event: AstrMessageEvent, keyword: str):
        # 参数错位修正
        the_real_event_obj = event

        if not keyword:
            yield the_real_event_obj.plain_result("请提供要搜索的关键词！\n用法：78dm <关键词>")
            return
        
        parts = keyword.split()
        search_keyword = ""
        max_pages = 1
        MAX_PAGE_LIMIT = 5 

        if len(parts) > 1 and parts[-1].isdigit():
            search_keyword = " ".join(parts[:-1])
            max_pages = max(1, min(int(parts[-1]), MAX_PAGE_LIMIT))
        else:
            search_keyword = keyword
        
        if not search_keyword:
            yield the_real_event_obj.plain_result("关键词不能为空！\n用法：78dm <关键词>")
            return

        yield the_real_event_obj.plain_result(f"正在为'{search_keyword}'搜索模型信息，请稍候...")

        try:
            loop = asyncio.get_running_loop()
            products = await loop.run_in_executor(
                None, fetch_products_from_78dm, search_keyword, max_pages
            )

            if not products:
                yield the_real_event_obj.plain_result(f'未能找到与"{search_keyword}"相关的模型信息，请更换关键词再试。')
                return
            
            # 发送一条介绍性文本
            intro_text = f'为你找到关于"{search_keyword}"的 {len(products)} 条结果：'
            yield the_real_event_obj.plain_result(intro_text)

            # 为每个产品创建一个 Node，作为合并转发的一条消息
            nodes = []
            for product in products:
                # 每个产品的消息内容
                content = []
                
                text_part = (
                    f"名称: {product.get('name', 'N/A')}\n"
                    f"类型: {product.get('type', 'N/A')}\n"
                    f"厂商: {product.get('manufacturer', 'N/A')}\n"
                    f"发售: {product.get('release_date', 'N/A')}\n"
                    f"价格: {product.get('price', 'N/A')}\n"
                    f"链接: {product.get('product_url', 'N/A')}"
                )
                
                if image_url := product.get('image_url'):
                    content.append(Comp.Image.fromURL(url=image_url))
                
                content.append(Comp.Plain(text=text_part))

                # 创建 Node
                node = Comp.Node(
                    uin=the_real_event_obj.get_self_id(),
                    name=product.get('name', '搜索结果'), # 使用产品名作为气泡昵称
                    content=content
                )
                nodes.append(node)
            
            # 将所有独立的 Node 打包成一个 Comp.Nodes 组件，它代表一条完整的合并转发消息
            forward_message = Comp.Nodes(nodes=nodes)

            # 将这个合并转发组件作为链中的唯一元素，通过 chain_result 发送
            yield the_real_event_obj.chain_result([forward_message])

        except Exception as e:
            logger.error(f"[78animeSearch] 处理搜索命令时发生严重错误: {e}", exc_info=True)
            yield the_real_event_obj.plain_result("查询过程中出现了一些问题，请稍后再试或联系管理员查看后台日志。")
