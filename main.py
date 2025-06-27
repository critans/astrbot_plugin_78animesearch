# main.py

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


# --- 爬虫代码部分 (无变化) ---
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
        image_url = product_element.select_one('img.single-cover')['src'] if product_element.select_one('img.single-cover') else ""
        
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

# --- astrbot 插件主类 (修正参数错位问题) ---

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.name = "78动漫搜索插件"
        self.version = "1.3-dev"
        self.author = "critans"

    @filter.command("78dm", "78动漫", "模型搜索", prefixes=["", "/", "#"])
    async def handle_78dm_search(self, event: AstrMessageEvent, keyword: str):
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!                       最终的、反直觉的修正                     !!
        # !! 由于框架的参数注入问题，这里的 self 实际上是 event 对象,        !!
        # !! 而 event 实际上是 context 对象。                              !!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # 为代码可读性，我们先进行“拨乱反正”
        real_self = self # 这个才是真正的插件实例 self
        real_event = event # 这个才是真正的事件 event

        # 但根据报错，实际传入的对象是错位的
        # self -> event object
        # event -> context object
        
        # 因此我们这样使用：
        the_real_event_obj = self
        the_real_context_obj = event

        if not keyword:
            yield the_real_event_obj.plain_result("请提供要搜索的关键词！\n用法：78dm [关键词]")
            return
        
        yield the_real_event_obj.plain_result(f"正在为“{keyword}”搜索模型信息，请稍候...")

        try:
            # 使用 context 的 loop 来执行耗时操作
            products = await the_real_context_obj.loop.run_in_executor(
                None, fetch_products_from_78dm, keyword, 1
            )

            if not products:
                yield the_real_event_obj.plain_result(f"未能找到与“{keyword}”相关的模型信息，请更换关键词再试。")
                return

            yield the_real_event_obj.plain_result(f"为你找到以下关于“{keyword}”的结果：\n" + "-"*20)

            results_to_show = products[:3]
            for product in results_to_show:
                text_part = (
                    f"名称: {product.get('name', 'N/A')}\n"
                    f"类型: {product.get('type', 'N/A')}\n"
                    f"厂商: {product.get('manufacturer', 'N/A')}\n"
                    f"发售: {product.get('release_date', 'N/A')}\n"
                    f"价格: {product.get('price', 'N/A')}\n"
                    f"链接: {product.get('product_url', 'N/A')}"
                )
                
                message_chain = []
                if image_url := product.get('image_url'):
                    message_chain.append(Comp.Image.fromUrl(url=image_url))
                
                message_chain.append(Comp.Plain(text=text_part))
                
                yield the_real_event_obj.chain_result(message_chain)
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[78animeSearch] 处理搜索命令时发生严重错误: {e}", exc_info=True)
            yield the_real_event_obj.plain_result("查询过程中出现了一些问题，请稍后再试或联系管理员查看后台日志。")
