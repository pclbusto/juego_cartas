import os
import json
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

DB_FILE = "yugioh.db"
JSON_FILE = "normal_monsters.json"
IMAGES_DIR = "images"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            cid TEXT PRIMARY KEY,
            type TEXT,
            name TEXT,
            image_name TEXT,
            attribute TEXT,
            level TEXT,
            atk TEXT,
            def TEXT,
            text TEXT,
            image_url TEXT
        )
    ''')
    
    # Load JSON if table is empty
    cursor.execute("SELECT COUNT(*) FROM cards")
    if cursor.fetchone()[0] == 0:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                cards = json.load(f)
                for card in cards:
                    cursor.execute('''
                        INSERT INTO cards (cid, type, name, image_name, attribute, level, atk, def, text, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        card.get('cid', ''),
                        card.get('type', ''),
                        card.get('name', ''),
                        card.get('image_name', ''),
                        card.get('attribute', ''),
                        card.get('level', ''),
                        card.get('atk', ''),
                        card.get('def', ''),
                        card.get('text', ''),
                        card.get('image_url', '')
                    ))
            conn.commit()
    conn.close()

def get_cards():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards ORDER BY name")
    cards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cards

class YgoViewerWindow(Adw.ApplicationWindow):
    def __init__(self, app, cards):
        super().__init__(application=app, title="Yu-Gi-Oh! Card Viewer")
        self.set_default_size(800, 600)
        self.cards = cards
        
        # Make sure image directory exists
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)
        
        if not self.cards:
            placeholder = Adw.StatusPage(title="No Cards Found", description="El archivo normal_monsters.json está vacío o no se encontró.")
            main_box.append(placeholder)
            return
            
        # Paned view for List / Details
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(300)
        paned.set_vexpand(True)
        main_box.append(paned)
        
        # Left side: List
        list_scrolled = Gtk.ScrolledWindow()
        list_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        paned.set_start_child(list_scrolled)
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-selected", self.on_row_selected)
        list_scrolled.set_child(self.listbox)
        
        # Right side: Details
        details_scrolled = Gtk.ScrolledWindow()
        paned.set_end_child(details_scrolled)
        
        # We need an alignment box or just a vertical box
        self.details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.details_box.set_margin_top(24)
        self.details_box.set_margin_bottom(24)
        self.details_box.set_margin_start(24)
        self.details_box.set_margin_end(24)
        
        # Set alignment to focus details in the center horizontally
        self.details_box.set_halign(Gtk.Align.CENTER)
        self.details_box.set_size_request(400, -1)
        
        # Image
        self.card_image = Gtk.Picture()
        self.card_image.set_size_request(300, 437) # Approx ygo card ratio
        self.card_image.set_halign(Gtk.Align.CENTER)
        
        # Name
        self.name_label = Gtk.Label()
        self.name_label.add_css_class("title-1")
        self.name_label.set_wrap(True)
        self.name_label.set_justify(Gtk.Justification.CENTER)
        
        # Stats ListBox
        prefs_group = Adw.PreferencesGroup()
        self.stats_listbox = Gtk.ListBox()
        self.stats_listbox.add_css_class("boxed-list")
        self.stats_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        prefs_group.add(self.stats_listbox)
        
        # Description
        self.desc_label = Gtk.Label()
        self.desc_label.set_wrap(True)
        self.desc_label.set_justify(Gtk.Justification.LEFT)
        self.desc_label.add_css_class("body")
        
        # Build layout
        self.details_box.append(self.card_image)
        self.details_box.append(self.name_label)
        self.details_box.append(prefs_group)
        self.details_box.append(Gtk.Separator())
        self.details_box.append(self.desc_label)
        
        details_scrolled.set_child(self.details_box)
        
        # Thread pool for downloading images
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Populate List
        for card in self.cards:
            row = Adw.ActionRow(title=card['name'], subtitle=f"{card['attribute']} | {card['level']}")
            row.card_data = card
            self.listbox.append(row)
            
        # Select first row
        if self.cards:
            first_row = self.listbox.get_row_at_index(0)
            self.listbox.select_row(first_row)

    def on_row_selected(self, listbox, row):
        if not row:
            return
            
        card = row.card_data
        
        # Update labels
        self.name_label.set_text(card.get('name', 'Unknown'))
        self.desc_label.set_text(card.get('text', 'No description available.'))
        
        # Clear old stats
        while self.stats_listbox.get_first_child():
            self.stats_listbox.remove(self.stats_listbox.get_first_child())
            
        # Add stats
        stats = [
            ("Attribute", card.get('attribute', '-')),
            ("Level", card.get('level', '-')),
            ("Type", card.get('type', '-')),
            ("ATK", str(card.get('atk', '-'))),
            ("DEF", str(card.get('def', '-')))
        ]
        
        for key, val in stats:
            stat_row = Adw.ActionRow(title=key)
            val_label = Gtk.Label(label=val)
            val_label.add_css_class("dim-label")
            stat_row.add_suffix(val_label)
            self.stats_listbox.append(stat_row)
            
        # Handle Image Loading
        cid = card.get('cid')
        image_url = card.get('image_url')
        if cid and image_url:
            image_path = os.path.join(IMAGES_DIR, f"{cid}.jpg")
            if os.path.exists(image_path):
                self.card_image.set_filename(image_path)
            else:
                self.card_image.set_filename(None) # Clear current
                self.executor.submit(self.download_image, image_url, image_path, cid)

    def download_image(self, url, filepath, cid):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            
            # Update UI on main thread
            GLib.idle_add(self.image_downloaded, filepath, cid)
        except Exception as e:
            print(f"Error downloading image: {e}")

    def image_downloaded(self, filepath, cid):
        row = self.listbox.get_selected_row()
        if row:
            card = row.card_data
            if card.get('cid') == cid:
                self.card_image.set_filename(filepath)

class YgoApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.YgoViewer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        
    def do_activate(self):
        init_db()
        cards = get_cards()
        
        win = self.props.active_window
        if not win:
            win = YgoViewerWindow(self, cards)
        win.present()

if __name__ == "__main__":
    app = YgoApp()
    app.run(None)
