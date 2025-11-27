import requests
from bs4 import BeautifulSoup

def scrape_page(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.string if soup.title else ""

    docs = []
    h1 = h2 = None

    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        if tag.name == 'h1':
            h1 = tag.get_text(strip=True)
            h2 = None
        elif tag.name == 'h2':
            h2 = tag.get_text(strip=True)
        else:
            text = tag.get_text(strip=True)
            if len(text) < 20:
                continue

            docs.append({
                "heading": h1 or page_title,
                "subheading": h2,
                "content": text,
                "source": "website",
                "url": url
            })

    return docs
