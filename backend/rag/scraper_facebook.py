import requests
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
TOKEN = os.getenv("FACEBOOK_TOKEN")

def fetch_facebook_posts():
    url = f"https://graph.facebook.com/{PAGE_ID}/posts?access_token={TOKEN}"
    res = requests.get(url).json()

    posts = []
    for p in res.get("data", []):
        posts.append({
            "heading": "Facebook Post",
            "subheading": p.get("created_time"),
            "content": p.get("message", ""),
            "source": "facebook"
        })
    return posts
