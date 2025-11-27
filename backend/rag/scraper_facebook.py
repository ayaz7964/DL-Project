# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()

# PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
# TOKEN = os.getenv("FACEBOOK_TOKEN")

# def fetch_facebook_posts():
#     url = f"https://graph.facebook.com/{PAGE_ID}/posts?access_token={TOKEN}"
#     res = requests.get(url).json()

#     posts = []
#     for p in res.get("data", []):
#         posts.append({
#             "heading": "Facebook Post",
#             "subheading": p.get("created_time"),
#             "content": p.get("message", ""),
#             "source": "facebook"
#         })
#     return posts


# rag/scraper_facebook.py
import os
import requests
from dotenv import load_dotenv
load_dotenv()

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
TOKEN = os.getenv("FACEBOOK_TOKEN")

def fetch_facebook_posts(limit=50):
    if not PAGE_ID or not TOKEN:
        print("FB credentials missing; skipping FB scrape")
        return []
    url = f"https://graph.facebook.com/{PAGE_ID}/posts"
    params = {"access_token": TOKEN, "limit": limit, "fields": "message,created_time,permalink_url"}
    res = requests.get(url, params=params, timeout=15).json()
    out = []
    for p in res.get("data", []):
        message = p.get("message") or ""
        if len(message) < 10:
            continue
        out.append({
            "heading": "Facebook update",
            "subheading": p.get("created_time"),
            "content": message,
            "source": "facebook",
            "url": p.get("permalink_url")
        })
    return out
