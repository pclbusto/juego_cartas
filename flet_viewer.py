import os
import urllib.request
import threading
import flet as ft
from database import DatabaseManager

DB_FILE = "yugioh.db"
JSON_FILE = "normal_monsters.json"
IMAGES_DIR = "images"

def main(page: ft.Page):
    page.title = "Yu-Gi-Oh! Deck Builder"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window.width = 1100
    page.window.height = 800
    page.padding = 0

    db = DatabaseManager(DB_FILE)
    db.init_db(JSON_FILE)
    all_cards = db.get_cards()

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    # Multi-deck state
    decks = db.get_all_decks()
    if not decks:
        db.create_deck("Main Deck")
        decks = db.get_all_decks()
    
    current_deck_id = decks[0]['id']
    deck_cards = []

    # Deck Selector
    def on_deck_change(e):
        nonlocal current_deck_id
        current_deck_id = int(deck_dropdown.value)
        refresh_deck_list()
        if is_in_deck_view:
            switch_tabs(True)
        page.update()

    deck_dropdown = ft.Dropdown(
        label="Select Deck",
        options=[ft.dropdown.Option(str(d['id']), d['name']) for d in decks],
        value=str(current_deck_id),
        width=200
    )
    deck_dropdown.on_change = on_deck_change

    def on_new_deck(e):
        def close_dlg(e):
            page.dialog.open = False
            page.update()

        def create_dlg(e):
            name = name_field.value.strip()
            if name:
                db.create_deck(name)
                refresh_decks()
                page.dialog.open = False
                page.update()

        name_field = ft.TextField(label="Deck Name")
        dlg = ft.AlertDialog(
            title=ft.Text("Create New Deck"),
            content=name_field
        )
        cancel_btn = ft.TextButton("Cancel")
        cancel_btn.on_click = close_dlg
        create_btn = ft.TextButton("Create")
        create_btn.on_click = create_dlg
        dlg.actions = [cancel_btn, create_btn]
        
        page.dialog = dlg
        page.dialog.open = True
        page.update()

    new_deck_btn = ft.IconButton(icon="add")
    new_deck_btn.on_click = on_new_deck

    def refresh_decks():
        nonlocal decks
        decks = db.get_all_decks()
        deck_dropdown.options = [ft.dropdown.Option(str(d['id']), d['name']) for d in decks]
        page.update()

    # UI Components for Details
    card_image = ft.Image(src="", width=300, height=437, fit=ft.BoxFit.CONTAIN, border_radius=10)
    image_container = ft.Container(
        content=card_image, width=300, height=437, alignment=ft.Alignment(0, 0),
        bgcolor="surfacevariant", border_radius=10, margin=ft.Margin(0, 0, 0, 16)
    )
    name_label = ft.Text("Select a card", size=24, weight="bold", text_align=ft.TextAlign.CENTER)
    desc_label = ft.Text("", size=14, text_align=ft.TextAlign.LEFT)
    stats_column = ft.Column(spacing=0)
    
    # Action Buttons
    def add_to_deck_click(e):
        if current_card:
            success = db.add_card_to_deck(current_deck_id, current_card['cid'])
            if success:
                page.snack_bar = ft.SnackBar(ft.Text(f"Added {current_card['name']} to deck"))
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Could not add more copies (max 3 or deck full)"))
            page.snack_bar.open = True
            refresh_deck_list()
            page.update()

    def remove_from_deck_click(e):
        if current_card:
            db.remove_card_from_deck(current_deck_id, current_card['cid'])
            page.snack_bar = ft.SnackBar(ft.Text(f"Removed copy from deck"))
            page.snack_bar.open = True
            refresh_deck_list()
            # If we were in deck view and card is gone, clear details
            in_deck = any(c['cid'] == current_card['cid'] for c in deck_cards)
            if not in_deck and is_in_deck_view:
                update_details(None)
            page.update()

    add_button = ft.Button("Add to Deck", icon="add", visible=False)
    add_button.on_click = add_to_deck_click
    remove_button = ft.Button("Remove", icon="delete", visible=False)
    remove_button.on_click = remove_from_deck_click

    details_pane = ft.Column(
        [
            image_container,
            name_label,
            ft.Row([add_button, remove_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Card(content=ft.Container(content=stats_column, padding=10), margin=ft.Margin(0, 16, 0, 16)),
            desc_label
        ],
        scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10
    )

    # State variables
    current_card = None
    current_list_index = 0
    is_in_deck_view = False

    def update_details(card):
        nonlocal current_card
        current_card = card
        
        if not card:
            name_label.value = "Select a card"
            desc_label.value = ""
            card_image.src = None
            stats_column.controls.clear()
            add_button.visible = False
            remove_button.visible = False
            page.update()
            return

        name_label.value = card.get('name', 'Unknown')
        desc_label.value = card.get('text', '')
        
        # Buttons visibility
        add_button.visible = not is_in_deck_view
        remove_button.visible = is_in_deck_view

        # Stats
        stats_column.controls.clear()
        stats = [
            ("Attribute", card.get('attribute', '-')),
            ("Level", card.get('level', '-')),
            ("Type", card.get('type', '-')),
            ("ATK", str(card.get('atk', '-'))),
            ("DEF", str(card.get('def', '-')))
        ]
        for i, (key, val) in enumerate(stats):
            stats_column.controls.append(
                ft.Container(
                    content=ft.Row([ft.Text(key), ft.Text(val, color="onsurfacevariant")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(4, 8, 4, 8),
                    border=ft.Border(bottom=ft.BorderSide(1, "outlinevariant")) if i < len(stats)-1 else None
                )
            )

        # Image
        cid = card.get('cid')
        if cid:
            image_path = os.path.join(IMAGES_DIR, f"{cid}.jpg")
            if os.path.exists(image_path):
                card_image.src = os.path.abspath(image_path)
            else:
                card_image.src = None
                if card.get('image_url'):
                    def download():
                        try:
                            req = urllib.request.Request(card['image_url'], headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as resp:
                                with open(image_path, 'wb') as f: f.write(resp.read())
                            if current_card and current_card.get('cid') == cid:
                                card_image.src = os.path.abspath(image_path)
                                page.update()
                        except: pass
                    threading.Thread(target=download, daemon=True).start()
        
        page.update()

    # Lists
    browser_list = ft.ListView(expand=True, spacing=0)
    deck_list = ft.ListView(expand=True, spacing=0)

    def on_tile_click(e):
        nonlocal current_list_index
        current_list_index = e.control.data
        target_list = deck_list if is_in_deck_view else browser_list
        for i, c in enumerate(target_list.controls):
            c.bgcolor = "surfacevariant" if i == current_list_index else None
        
        card = (deck_cards if is_in_deck_view else all_cards)[current_list_index]
        update_details(card)

    def populate_list(l, items):
        l.controls.clear()
        for i, card in enumerate(items):
            title_text = card['name']
            if 'quantity' in card:
                title_text += f" x{card['quantity']}"
            
            c = ft.Container(
                content=ft.ListTile(title=ft.Text(title_text), subtitle=ft.Text(f"{card['attribute']} | Lvl {card['level']}")),
                data=i, border_radius=8
            )
            c.on_click = on_tile_click
            l.controls.append(c)

    def refresh_deck_list():
        nonlocal deck_cards
        deck_cards = db.get_deck_cards(current_deck_id)
        populate_list(deck_list, deck_cards)
        deck_btn.text = f"My Deck ({db.get_deck_card_count(current_deck_id)})"

    # Custom Tab Switcher
    browser_btn = ft.TextButton("All Cards", style=ft.ButtonStyle(color="primary"))
    browser_btn.on_click = lambda _: switch_tabs(False)
    deck_btn = ft.TextButton("My Deck (0)")
    deck_btn.on_click = lambda _: switch_tabs(True)
    
    tab_row = ft.Row([browser_btn, deck_btn], alignment=ft.MainAxisAlignment.START)
    list_content = ft.Container(content=browser_list, expand=True)

    def switch_tabs(to_deck):
        nonlocal is_in_deck_view, current_list_index
        is_in_deck_view = to_deck
        current_list_index = 0
        
        browser_btn.style.color = "secondary" if is_in_deck_view else "primary"
        deck_btn.style.color = "primary" if is_in_deck_view else "secondary"
        
        list_content.content = deck_list if is_in_deck_view else browser_list
        update_details(None)
        page.update()

    populate_list(browser_list, all_cards)
    refresh_deck_list()

    left_panel = ft.Column([
        ft.Row([deck_dropdown, new_deck_btn], spacing=10),
        tab_row, 
        list_content
    ], expand=True, spacing=10)

    def on_keyboard(e: ft.KeyboardEvent):
        nonlocal current_list_index
        items = deck_cards if is_in_deck_view else all_cards
        if not items: return
        if e.key == "Arrow Down" and current_list_index < len(items) - 1:
            current_list_index += 1
        elif e.key == "Arrow Up" and current_list_index > 0:
            current_list_index -= 1
        else: return
        
        target_list = deck_list if is_in_deck_view else browser_list
        for i, c in enumerate(target_list.controls):
            c.bgcolor = "surfacevariant" if i == current_list_index else None
        update_details(items[current_list_index])

    page.on_keyboard_event = on_keyboard
    
    page.add(
        ft.Row([
            ft.Container(content=left_panel, expand=1, border=ft.border.only(right=ft.border.BorderSide(1, "outlinevariant")), padding=10),
            ft.Container(content=details_pane, expand=2, padding=24, alignment=ft.Alignment(0, -1))
        ], expand=True, spacing=0)
    )

if __name__ == "__main__":
    ft.app(main)
