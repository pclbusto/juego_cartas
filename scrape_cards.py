import requests
from bs4 import BeautifulSoup
import json
import re
import argparse

def scrape_cards():
    parser = argparse.ArgumentParser(description="Scrape Yu-Gi-Oh! Cards")
    parser.add_argument("--type", type=str, choices=["monster", "spell", "trap"], default="monster", help="Card type to scrape")
    parser.add_argument("--subtype", type=str, help="Subtype (e.g., normal, effect, fusion, ritual, synchro, field, continuous, etc.)")
    parser.add_argument("--limit", type=int, default=-1, help="Number of cards to scrape (default: -1 = all)")
    parser.add_argument("--lang", type=str, default="en", help="Locale for card names/text: 'en' or 'es' (default: en)")
    args = parser.parse_args()

    card_limit = args.limit  # -1 = sin límite
    
    # Mapping for card types
    type_map = {
        "monster": "1",
        "spell": "2",
        "trap": "3"
    }
    
    # Mapping for common subtypes (othercon parameter or similar)
    # This is a bit complex as it depends on the site's internal IDs.
    # For now, we use the user-provided 'othercon=2' for normal monsters.
    subtype_params = ""
    if args.type == "monster":
        if args.subtype == "normal":
            subtype_params = "&othercon=2"
        elif args.subtype == "effect":
            subtype_params = "&othercon=3"
        elif args.subtype == "fusion":
            subtype_params = "&othercon=4"
        elif args.subtype == "ritual":
            subtype_params = "&othercon=5"
        elif args.subtype == "synchro":
            subtype_params = "&othercon=6"
        elif args.subtype == "xyz":
            subtype_params = "&othercon=7"
        elif args.subtype == "pendulum":
            subtype_params = "&othercon=8"
        elif args.subtype == "link":
            subtype_params = "&othercon=9"
    elif args.type == "spell":
        # Spells and Traps might use different parameters or ctype subcategories
        # For now, we'll stick to the base ctype provided by the user.
        pass

    lang_header = "es-ES,es;q=0.9,en;q=0.8" if args.lang == 'es' else "en-US,en;q=0.9,es;q=0.8"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": lang_header,
    }

    cards_data = []
    page = 1

    print(f"Fetching list of {args.type.capitalize()}s (Limit: {card_limit})...")
    
    while (card_limit == -1 or len(cards_data) < card_limit):
        # Base URL from user request, adapted for parameters
        url = (f"https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=1&sess=1&rp=100&mode=&sort=1&keyword="
               f"&stype=1&ctype={type_map[args.type]}{subtype_params}&page={page}&request_locale={args.lang}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            card_elements = soup.select('.t_row')
            
            if not card_elements:
                print(f"No more cards found on page {page}. Stopping.")
                break
                
            for el in card_elements:
                if len(cards_data) >= card_limit:
                    break
                    
                card_info = {}
                
                # Name
                name_span = el.select_one('.card_name')
                if not name_span:
                    continue
                card_info['name'] = re.sub(r'\s+', ' ', name_span.get_text(strip=True))
                
                # Species / Type
                spec_span = el.select_one('.card_info_species_and_other_item span')
                if spec_span:
                    card_info['type'] = re.sub(r'\s+', ' ', spec_span.get_text(strip=True))
                
                # CID for images
                cid_input = el.select_one('input.cid')
                cid = None
                if cid_input:
                    cid = cid_input.get('value')
                
                if cid:
                    card_info['image_name'] = f"{cid}.jpg"
                    card_info['cid'] = cid
                    card_info['image_url'] = f"https://www.db.yugioh-card.com/yugiohdb/get_image.action?type=1&osys=1&cid={cid}"
                    
                # Attribute (Icons for Spell/Trap)
                attr_span = el.select_one('.box_card_attribute span')
                if attr_span:
                    card_info['attribute'] = attr_span.get_text(strip=True)
                
                # Monster specific fields
                if args.type == "monster":
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

    print(f"Found {len(cards_data)} cards.")

    output_file = f"{args.type}s_{args.lang}.json"
    if args.subtype:
        output_file = f"{args.subtype}_{args.type}s_{args.lang}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cards_data, f, ensure_ascii=False, indent=4)
        
    print(f"\nSuccessfully saved {len(cards_data)} cards to {output_file}")

if __name__ == "__main__":
    scrape_cards()
