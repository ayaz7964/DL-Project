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
from urllib.parse import urljoin, urlparse
from collections import deque
import os

# Disable SSL warnings because SIBA has misconfigured HTTPS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "300"))


def clean_text(t):
    return re.sub(r'\s+', ' ', t).strip()


def scrape_page(url, session=None):
    """
    Scrapes a single webpage.
    - Ignores SSL errors (verify=False)
    - Extracts h1/h2/p/li/h3 in document order
    - Returns structured docs for RAG plus parsed soup
    """
    s = session or requests

    try:
        r = s.get(url, timeout=15, verify=False)
        r.raise_for_status()
    except Exception as e:
        print("scrape error:", url, e)
        return [], None

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

    return data, soup


def _extract_links(soup, base_url, allowed_netloc):
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != allowed_netloc:
            continue
        if full.lower().endswith((".pdf", ".jpg", ".png", ".jpeg", ".gif", ".zip", ".rar")):
            continue
        links.add(full.split("#")[0])
    return links


def crawl_site(start_urls, max_pages=DEFAULT_MAX_PAGES):
    """
    BFS crawl within the same domain as the first URL; returns aggregated docs.
    """
    if not start_urls:
        return []
    seed = start_urls[0]
    domain = urlparse(seed).netloc
    queue = deque(start_urls)
    seen = set()
    all_docs = []
    session = requests.Session()

    while queue and len(seen) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        docs, soup = scrape_page(url, session=session)
        all_docs.extend(docs)
        if soup is None:
            continue
        for link in _extract_links(soup, url, domain):
            if link not in seen and len(seen) + len(queue) < max_pages:
                queue.append(link)

    print(f"[crawl] visited {len(seen)} pages, collected {len(all_docs)} sections.")
    return all_docs


def crawl_and_collect(start_urls):
    """
    Legacy helper: single-pass scrape of provided URLs (no recursion).
    """
    all_docs = []
    for u in start_urls:
        result, _ = scrape_page(u)
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

