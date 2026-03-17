import requests
from bs4 import BeautifulSoup
import json
import re
import time
import argparse

parser = argparse.ArgumentParser(description="Scrape Yu-Gi-Oh! Normal Monsters")
parser.add_argument("--limit", type=int, default=10, help="Number of cards to scrape (default: 10)")
args = parser.parse_args()

card_limit = args.limit

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8"
}

cards_data = []
page = 1

print(f"Fetching list of Normal Monsters (Limit: {card_limit})...")
while len(cards_data) < card_limit and page <= 50:
    # Adding &rp=100 to get 100 results per page, minimizing pagination requests
    url = f"https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=1&stype=1&ctype=1&rp=100&page={page}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        card_elements = soup.select('.t_row')
        
        if not card_elements:
            # Reached a page with no cards, no need to keep paginating
            print(f"No more cards found on page {page}. Stopping.")
            break
            
        for el in card_elements:
            if len(cards_data) >= card_limit:
                break
                
            card_info = {}
            
            # Type (Species)
            spec_span = el.select_one('.card_info_species_and_other_item span')
            if spec_span:
                type_text = re.sub(r'\s+', ' ', spec_span.get_text(strip=True))
                if 'Normal' not in type_text or 'Effect' in type_text:
                    continue
                card_info['type'] = type_text
            else:
                continue
            
            # Name
            name_span = el.select_one('.card_name')
            if not name_span:
                continue
            card_info['name'] = re.sub(r'\s+', ' ', name_span.get_text(strip=True))
            
            # CID
            cid_input = el.select_one('input.cid')
            cid = None
            if cid_input:
                cid = cid_input.get('value')
            else:
                link_input = el.select_one('input.link_value')
                if link_input:
                    match = re.search(r'cid=(\d+)', link_input.get('value', ''))
                    if match:
                        cid = match.group(1)
            
            if cid:
                card_info['image_name'] = f"{cid}.jpg"
                card_info['cid'] = cid
                
            # Attribute
            attr_span = el.select_one('.box_card_attribute span')
            if attr_span:
                card_info['attribute'] = attr_span.get_text(strip=True)
                
            # Level
            level_span = el.select_one('.box_card_level_rank span')
            if level_span:
                card_info['level'] = level_span.get_text(strip=True)
                
            # ATK
            atk_span = el.select_one('.atk_power span')
            if atk_span:
                card_info['atk'] = atk_span.get_text(strip=True).replace('ATK ', '')
                
            # DEF
            def_span = el.select_one('.def_power span')
            if def_span:
                card_info['def'] = def_span.get_text(strip=True).replace('DEF ', '')
                
            # Text / Effect
            text_dd = el.select_one('.box_card_text')
            if text_dd:
                card_info['text'] = text_dd.get_text(strip=True)
                
            cards_data.append(card_info)
    else:
        print(f"Failed to fetch page {page}: {response.status_code}")
        break
        
    page += 1

print(f"Found {len(cards_data)} cards. Fetching real image URLs...")

# Second pass: fetch the detail page for each card to get the real encrypted image URL
for card in cards_data:
    if 'cid' in card:
        detail_url = f"https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=2&cid={card['cid']}"
        try:
            time.sleep(1) # Be polite to the server
            res = requests.get(detail_url, headers=headers)
            if res.status_code == 200:
                detail_soup = BeautifulSoup(res.text, 'html.parser')
                # The real image URL with the 'enc' token is often in the og:image meta tag
                meta_img = detail_soup.find('meta', property='og:image')
                if meta_img and meta_img.get('content'):
                    card['image_url'] = meta_img['content']
                else:
                    # Fallback just in case
                    card['image_url'] = f"https://www.db.yugioh-card.com/yugiohdb/get_image.action?type=1&osys=1&cid={card['cid']}"
                print(f"[{card['name']}] Found image URL: {card['image_url']}")
        except Exception as e:
            print(f"Error fetching detail for {card['name']}: {e}")

with open('normal_monsters.json', 'w', encoding='utf-8') as f:
    json.dump(cards_data, f, ensure_ascii=False, indent=4)
    
print(f"\nSuccessfully saved {len(cards_data)} normal monsters to normal_monsters.json")
