# import requests
# from bs4 import BeautifulSoup

# def scrape_page(url):
#     html = requests.get(url).text
#     soup = BeautifulSoup(html, "html.parser")

#     page_title = soup.title.string if soup.title else ""

#     docs = []
#     h1 = h2 = None

#     for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
#         if tag.name == 'h1':
#             h1 = tag.get_text(strip=True)
#             h2 = None
#         elif tag.name == 'h2':
#             h2 = tag.get_text(strip=True)
#         else:
#             text = tag.get_text(strip=True)
#             if len(text) < 20:
#                 continue

#             docs.append({
#                 "heading": h1 or page_title,
#                 "subheading": h2,
#                 "content": text,
#                 "source": "website",
#                 "url": url
#             })

#     return docs


# rag/scraper_web.py
import requests
from bs4 import BeautifulSoup
import re
import hashlib
import urllib3

# Disable SSL warnings because SIBA has misconfigured HTTPS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def clean_text(t):
    return re.sub(r'\s+', ' ', t).strip()


def scrape_page(url, session=None):
    """
    Scrapes a single webpage.
    - Ignores SSL errors (verify=False)
    - Extracts h1/h2/p/li/h3 in document order
    - Returns structured docs for RAG
    """
    s = session or requests

    try:
        # IMPORTANT FIX: bypass SSL certificate verification
        r = s.get(url, timeout=15, verify=False)
        r.raise_for_status()
    except Exception as e:
        print("scrape error:", url, e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    title_node = soup.title.string if soup.title else None
    page_title = title_node.strip() if title_node else None

    data = []
    current_h1 = None
    current_h2 = None

    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        if tag.name == 'h1':
            current_h1 = tag.get_text(strip=True)
            current_h2 = None
        elif tag.name == 'h2':
            current_h2 = tag.get_text(strip=True)
        elif tag.name in ['p', 'li', 'h3']:
            text = tag.get_text(strip=True)
            if len(text) < 20:
                continue
            data.append({
                "heading": current_h1 or page_title,
                "subheading": current_h2,
                "content": text,
                "source": "website",
                "url": url
            })

    return data


def crawl_and_collect(start_urls):
    """
    Takes a list of URLs and returns all extracted docs.
    """
    all_docs = []
    for u in start_urls:
        result = scrape_page(u)
        all_docs.extend(result)
    return all_docs


def hash_docs(docs):
    """
    Deterministic hash of scraped docs to detect changes.
    """
    m = hashlib.md5()
    for d in docs:
        for key in ("heading", "subheading", "content", "url"):
            val = d.get(key) or ""
            m.update(val.encode("utf-8", errors="ignore"))
    return m.hexdigest()

