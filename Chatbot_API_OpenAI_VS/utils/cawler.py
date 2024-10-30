import requests
import time
from bs4 import BeautifulSoup
from prepare_vector_db import add_vector_db
import openai

robots_context = """
 'https://travel.com.vn/cam-nang-du-lich/sitemap.xml'
"""
# """
# Sitemap: https://travel.com.vn/sitemap.xml
# Sitemap: https://travel.com.vn/du-lich/sitemap.xml
# Sitemap: https://travel.com.vn/kinh-nghiem-du-lich/sitemap.xml
# """
def parse_robots_context(context):
    urls = [url.strip().strip("'") for url in context.strip().split(',')]
    return urls

def fetch_sitemap(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Không thể tải sitemap từ {url}: {e}")
        return None

def parse_sitemap(xml):
    soup = BeautifulSoup(xml, 'xml')
    urls = [loc.text for loc in soup.find_all('loc')]
    return urls

def add_all_links():
    sitemap_urls = parse_robots_context(robots_context)
    all_links = []

    for sitemap_url in sitemap_urls:
        xml = fetch_sitemap(sitemap_url)
        if xml:
            links = parse_sitemap(xml)
            all_links.extend(links)

    return all_links

all_links = add_all_links()
print("Các liên kết thu được từ các tệp Sitemap:")
for link in all_links:
    print(link)
print(len(all_links))

def fetch_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Không thể lấy dữ liệu từ {url}: {e}")
        return None

def parse_content(html, link):
    soup = BeautifulSoup(html, 'html.parser')
    for unwanted_div in soup.find_all(class_='header'):
        unwanted_div.decompose()
    for unwanted_div in soup.find_all(class_='footer--container'):
        unwanted_div.decompose()
    for unwanted_div in soup.find_all(class_='find-tour-content'):
        unwanted_div.decompose()
    for unwanted_div in soup.find_all(class_='tour-similar'):
        unwanted_div.decompose()
    for unwanted_div in soup.find_all(class_='right sidebar'):
        unwanted_div.decompose()

    content = soup.get_text(strip=True)
    if not content:
        return ""
    content_with_link = f"{content} - Để biết thêm thông tin hãy truy cập: {link}.\n"
    return content_with_link

def get_content(link):
    html = fetch_page(link)
    if html:
        content = parse_content(html, link)
        return content
    return ""

def web_cawler():
    for link in all_links:
        try:
            content = get_content(link)
            if content:
                add_vector_db(content)
            time.sleep(1)
        except Exception as e:
            print(f"Lỗi xảy ra khi xử lý {link}: {e}")
            time.sleep(5)  # Tạm dừng lâu hơn trước khi thử lại
#
# def web_cawler():
#     for link in all_links:
#         if link.startswith("https://travel.com.vn/du-lich-trong-nuoc"):
#             try:
#                 content = get_content(link)
#                 if content:
#                     add_vector_db(content)
#                 time.sleep(1)
#             except Exception as e:
#                 print(f"Lỗi xảy ra khi xử lý {link}: {e}")
#                 time.sleep(5)  # Tạm dừng lâu hơn trước khi thử lại
web_cawler()
