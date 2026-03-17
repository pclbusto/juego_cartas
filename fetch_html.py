import requests
from bs4 import BeautifulSoup
import json

url = "https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=1&stype=1&ctype=1&othercon=1&page=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    with open('/tmp/ygo_search.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("Saved HTML to /tmp/ygo_search.html")
else:
    print(f"Error {response.status_code}")
