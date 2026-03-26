import os
import re
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import random

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from database import DatabaseManager

DB_FILE = "yugioh.db"
IMAGES_DIR = "images"
SETTINGS_FILE = "settings.json"


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_settings(data: dict):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


class YgoViewerWindow(Adw.ApplicationWindow):
    def __init__(self, app, cards):
        super().__init__(application=app, title="Yu-Gi-Oh! Card Viewer")
        settings = _load_settings()
        self.set_default_size(settings.get("width", 900), settings.get("height", 600))
        self.connect("close-request", self._on_close)
        self.cards = cards
        self.db = DatabaseManager()
        self.lang = "es" if "es" in self.db.get_available_languages() else "en"
        
        # Reload cards with correct initial language if needed
        if self.lang != "en":
            self.cards = self.db.get_cards(lang=self.lang)

        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

        self.bg_download_thread = None
        self.bg_download_running = False
        self.bg_download_cancelled = False

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        if not self.cards:
            placeholder = Adw.StatusPage(
                title="No Cards Found",
                description="No se encontraron cartas en la base de datos. Ejecuta scrape_cards.py primero."
            )
            main_box.append(placeholder)
            return

        # Info toggle button in header
        self.info_btn = Gtk.ToggleButton(icon_name="dialog-information-symbolic")
        self.info_btn.set_tooltip_text("Estadísticas de la colección")
        self.info_btn.connect("toggled", self.on_info_toggled)

        # Hamburger Menu
        self.main_menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self.main_menu_btn.set_tooltip_text("Opciones adicionales")
        menu_popover = Gtk.Popover()
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu_box.set_margin_top(8)
        menu_box.set_margin_bottom(8)
        menu_box.set_margin_start(8)
        menu_box.set_margin_end(8)
        dl_btn = Gtk.Button(label="Descargar Faltantes (Bajo Perfil)")
        dl_btn.connect("clicked", self.start_bg_download)
        status_btn = Gtk.Button(label="Estado de Descargas")
        status_btn.connect("clicked", self.show_download_status)
        menu_box.append(dl_btn)
        menu_box.append(status_btn)
        menu_popover.set_child(menu_box)
        self.main_menu_btn.set_popover(menu_popover)
        
        header.pack_end(self.main_menu_btn)
        header.pack_end(self.info_btn)

        # Language Selection Button
        self.lang_btn = Gtk.MenuButton(icon_name="locale-symbolic")
        self.lang_btn.set_tooltip_text("Cambiar idioma")
        lang_popover = Gtk.Popover()
        lang_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lang_box.set_margin_top(8)
        lang_box.set_margin_bottom(8)
        lang_box.set_margin_start(8)
        lang_box.set_margin_end(8)
        
        for lcode in self.db.get_available_languages():
            lbtn = Gtk.Button(label=lcode.upper())
            lbtn.connect("clicked", self._on_lang_clicked, lcode)
            lang_box.append(lbtn)
            
        lang_popover.set_child(lang_box)
        self.lang_btn.set_popover(lang_popover)
        header.pack_end(self.lang_btn)

        # Filter button in header
        self.active_filters = {
            'main_types': set(), 'attributes': set(), 'subtypes': set(),
            'level_min': None, 'level_max': None,
            'atk_min': None,   'atk_max': None,
            'def_min': None,   'def_max': None,
            'no_image': False,
        }
        self.filter_type_btns = {}
        self.filter_attr_btns = {}
        self.filter_subtype_btns = {}
        self.filter_btn = Gtk.MenuButton(icon_name="funnel-symbolic")
        self.filter_btn.set_tooltip_text("Filtrar cartas")
        header.pack_end(self.filter_btn)

        # Overlay: paned is the base, info panel floats on top
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)
        main_box.append(overlay)

        # Paned: list | details (base layer)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(300)
        paned.set_hexpand(True)
        paned.set_vexpand(True)
        overlay.set_child(paned)

        # Left: search + card list
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        paned.set_start_child(left_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar por nombre...")
        self.search_entry.set_margin_top(6)
        self.search_entry.set_margin_bottom(6)
        self.search_entry.set_margin_start(6)
        self.search_entry.set_margin_end(6)
        self.search_entry.connect("search-changed", self._on_filter_changed)
        left_box.append(self.search_entry)

        list_scrolled = Gtk.ScrolledWindow()
        list_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scrolled.set_vexpand(True)
        left_box.append(list_scrolled)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-selected", self.on_row_selected)
        self.listbox.set_filter_func(self._filter_func)
        list_scrolled.set_child(self.listbox)

        # Right: two-column details layout (image | info)
        details_outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        details_outer.set_hexpand(True)
        details_outer.set_vexpand(True)
        paned.set_end_child(details_outer)

        # ── Left column: image (tamaño fijo, no se estira con la ventana) ──
        image_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        image_col.set_margin_top(16)
        image_col.set_margin_bottom(16)
        image_col.set_margin_start(16)
        image_col.set_margin_end(8)
        image_col.set_hexpand(False)
        image_col.set_vexpand(False)

        self.card_image = Gtk.Picture()
        self.card_image.set_can_shrink(False)
        self.card_image.set_size_request(220, 320)
        self.card_image.set_hexpand(False)
        self.card_image.set_vexpand(False)
        image_col.append(self.card_image)

        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_top(4)
        self.status_label.set_halign(Gtk.Align.CENTER)
        image_col.append(self.status_label)

        details_outer.append(image_col)
        details_outer.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # ── Right column: info (scrollable) ────────────────────────────────
        info_scrolled = Gtk.ScrolledWindow()
        info_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        info_scrolled.set_hexpand(True)
        info_scrolled.set_vexpand(True)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        info_box.set_margin_top(24)
        info_box.set_margin_bottom(24)
        info_box.set_margin_start(16)
        info_box.set_margin_end(24)

        self.name_label = Gtk.Label()
        self.name_label.set_selectable(True)
        self.name_label.add_css_class("title-1")
        self.name_label.set_wrap(True)
        self.name_label.set_halign(Gtk.Align.START)
        self.name_label.set_justify(Gtk.Justification.LEFT)

        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._stat_val_labels = []
        for _icon, _lbl in [
            ("tag-symbolic",                 "Atributo"),
            ("starred-symbolic",             "Nivel"),
            ("document-properties-symbolic", "Tipo"),
            ("go-up-symbolic",               "ATK"),
            ("go-down-symbolic",             "DEF"),
        ]:
            _row, _val = self._make_stat_row_reusable(_icon, _lbl, "-")
            self.stats_box.append(_row)
            self._stat_val_labels.append(_val)

        # Description with card-style background
        desc_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        desc_card.add_css_class("card")
        desc_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        desc_inner.set_margin_top(12)
        desc_inner.set_margin_bottom(12)
        desc_inner.set_margin_start(12)
        desc_inner.set_margin_end(12)

        self.desc_label = Gtk.Label()
        self.desc_label.set_selectable(True)
        self.desc_label.set_wrap(True)
        self.desc_label.set_halign(Gtk.Align.START)
        self.desc_label.set_justify(Gtk.Justification.LEFT)
        self.desc_label.add_css_class("body")
        desc_inner.append(self.desc_label)
        desc_card.append(desc_inner)

        info_box.append(self.name_label)
        info_box.append(self.stats_box)
        info_box.append(desc_card)
        info_scrolled.set_child(info_box)
        details_outer.append(info_scrolled)

        # Info panel as overlay (floats over the paned, anchored to the right)
        self.info_revealer = Gtk.Revealer()
        self.info_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self.info_revealer.set_transition_duration(200)
        self.info_revealer.set_halign(Gtk.Align.END)
        self.info_revealer.set_valign(Gtk.Align.FILL)
        self.info_revealer.set_child(self._build_info_panel())
        overlay.add_overlay(self.info_revealer)

        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.downloading_cids = set()
        self.queue_count = 0
        self._current_cid = None
        self.search_timeout_id = None

        # Populate list
        for card in self.cards:
            level = card.get('level')
            row = Adw.ActionRow(
                title=card['name'],
                subtitle=f"{card.get('attribute', '-')} | {level if level is not None else '-'}"
            )
            row.card_data = card
            self.listbox.append(row)

        self.filter_btn.set_popover(self._build_filter_popover())

        if self.cards:
            self.listbox.select_row(self.listbox.get_row_at_index(0))

    def _on_lang_clicked(self, btn, lcode):
        if self.lang == lcode:
            return
        self.lang = lcode
        self.lang_btn.get_popover().popdown()
        
        # Reload and refresh
        self.cards = self.db.get_cards(lang=self.lang)
        self._refresh_ui_after_lang_change()

    def _refresh_ui_after_lang_change(self):
        # Clear listbox
        while (row := self.listbox.get_first_child()):
            self.listbox.remove(row)
            
        # Re-populate
        for card in self.cards:
            level = card.get('level')
            row = Adw.ActionRow(
                title=card['name'],
                subtitle=f"{card.get('attribute', '-')} | {level if level is not None else '-'}"
            )
            row.card_data = card
            self.listbox.append(row)
            
        # Select first
        if self.cards:
            self.listbox.select_row(self.listbox.get_row_at_index(0))
        
        # Re-initialize popovers if they depend on card list (filters specifically)
        self.filter_btn.set_popover(self._build_filter_popover())
        self._refresh_info_panel()

    # ── Filter ────────────────────────────────────────────────────────────────

    SUBTYPE_KEYWORDS = [
        'Normal', 'Effect', 'Fusion', 'Ritual', 'Synchro',
        'XYZ', 'Pendulum', 'Link', 'Flip', 'Toon', 'Spirit',
        'Union', 'Gemini', 'Tuner',
    ]

    def _build_filter_popover(self):
        popover = Gtk.Popover()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(500)
        scrolled.set_propagate_natural_height(True)
        scrolled.set_size_request(320, -1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Collect unique values from cards
        attributes = sorted({
            c.get('attribute', '') for c in self.cards
            if c.get('attribute') and c.get('attribute') not in ('SPELL', 'TRAP', '')
        })
        subtypes_found = [kw for kw in self.SUBTYPE_KEYWORDS
                          if any(kw.lower() in c.get('type', '').lower() for c in self.cards)]

        # Tipo principal
        content.append(self._filter_label("Tipo"))
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for label, key in [("Monstruo", "monster"), ("Magia", "spell"), ("Trampa", "trap")]:
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class("pill")
            btn.connect("toggled", self._on_filter_changed)
            self.filter_type_btns[key] = btn
            type_box.append(btn)
        content.append(type_box)

        # Atributo
        if attributes:
            content.append(self._filter_label("Atributo"))
            attr_flow = Gtk.FlowBox()
            attr_flow.set_selection_mode(Gtk.SelectionMode.NONE)
            attr_flow.set_max_children_per_line(4)
            attr_flow.set_row_spacing(4)
            attr_flow.set_column_spacing(4)
            for attr in attributes:
                btn = Gtk.ToggleButton(label=attr)
                btn.add_css_class("pill")
                btn.connect("toggled", self._on_filter_changed)
                self.filter_attr_btns[attr] = btn
                attr_flow.append(btn)
            content.append(attr_flow)

        # Subtipo
        if subtypes_found:
            content.append(self._filter_label("Subtipo"))
            sub_flow = Gtk.FlowBox()
            sub_flow.set_selection_mode(Gtk.SelectionMode.NONE)
            sub_flow.set_max_children_per_line(3)
            sub_flow.set_row_spacing(4)
            sub_flow.set_column_spacing(4)
            for kw in subtypes_found:
                btn = Gtk.ToggleButton(label=kw)
                btn.add_css_class("pill")
                btn.connect("toggled", self._on_filter_changed)
                self.filter_subtype_btns[kw] = btn
                sub_flow.append(btn)
            content.append(sub_flow)

        # Estado
        content.append(self._filter_label("Estado"))
        estado_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.filter_no_img_btn = Gtk.ToggleButton(label="Falta Imagen")
        self.filter_no_img_btn.add_css_class("pill")
        self.filter_no_img_btn.connect("toggled", self._on_filter_changed)
        estado_box.append(self.filter_no_img_btn)
        content.append(estado_box)

        # Nivel
        content.append(self._filter_label("Nivel"))
        content.append(self._range_row("level", 0, 12, 1))

        # ATK
        content.append(self._filter_label("ATK"))
        content.append(self._range_row("atk", 0, 9999, 100))

        # DEF
        content.append(self._filter_label("DEF"))
        content.append(self._range_row("def", 0, 9999, 100))

        content.append(Gtk.Separator())
        clear_btn = Gtk.Button(label="Limpiar filtros")
        clear_btn.connect("clicked", self._clear_filters)
        content.append(clear_btn)

        scrolled.set_child(content)
        popover.set_child(scrolled)
        return popover

    def _filter_label(self, text):
        lbl = Gtk.Label(label=f"<b>{text}</b>", use_markup=True)
        lbl.set_halign(Gtk.Align.START)
        lbl.add_css_class("dim-label")
        return lbl

    def _range_row(self, key, min_val, max_val, step):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        spin_min = Gtk.SpinButton()
        spin_min.set_adjustment(Gtk.Adjustment(
            value=min_val, lower=min_val, upper=max_val, step_increment=step
        ))
        spin_min.set_width_chars(5)

        spin_max = Gtk.SpinButton()
        spin_max.set_adjustment(Gtk.Adjustment(
            value=max_val, lower=min_val, upper=max_val, step_increment=step
        ))
        spin_max.set_width_chars(5)

        spin_min.connect("value-changed", self._on_filter_changed)
        spin_max.connect("value-changed", self._on_filter_changed)

        setattr(self, f"spin_{key}_min", spin_min)
        setattr(self, f"spin_{key}_max", spin_max)
        setattr(self, f"spin_{key}_min_default", min_val)
        setattr(self, f"spin_{key}_max_default", max_val)

        lbl_min = Gtk.Label(label="Min:")
        lbl_min.add_css_class("dim-label")
        lbl_max = Gtk.Label(label="Max:")
        lbl_max.add_css_class("dim-label")

        box.append(lbl_min)
        box.append(spin_min)
        box.append(lbl_max)
        box.append(spin_max)
        return box

    def _on_filter_changed(self, widget=None):
        # Debounce search entry changes to 2 seconds
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = None

        if widget is self.search_entry:
            self.search_timeout_id = GLib.timeout_add(2000, self._do_filter)
        else:
            # Immediate for other filters (buttons, spinbuttons)
            self._do_filter()

    def _do_filter(self):
        self.search_timeout_id = None
        self.active_filters['main_types'] = {
            k for k, b in self.filter_type_btns.items() if b.get_active()
        }
        self.active_filters['attributes'] = {
            k for k, b in self.filter_attr_btns.items() if b.get_active()
        }
        self.active_filters['subtypes'] = {
            k for k, b in self.filter_subtype_btns.items() if b.get_active()
        }
        self.active_filters['no_image'] = getattr(self, 'filter_no_img_btn', None) and self.filter_no_img_btn.get_active()

        for key in ('level', 'atk', 'def'):
            if hasattr(self, f"spin_{key}_min"):
                v_min = int(getattr(self, f"spin_{key}_min").get_value())
                v_max = int(getattr(self, f"spin_{key}_max").get_value())
                d_min = getattr(self, f"spin_{key}_min_default")
                d_max = getattr(self, f"spin_{key}_max_default")
                self.active_filters[f'{key}_min'] = None if v_min == d_min else v_min
                self.active_filters[f'{key}_max'] = None if v_max == d_max else v_max

        self.listbox.invalidate_filter()
        self._update_filter_button()
        return False  # Stop the timeout

    def _filter_func(self, row):
        if not hasattr(row, 'card_data'):
            return True
        card = row.card_data
        f = self.active_filters
        attr = card.get('attribute', '')

        # Filtro de estado
        if f['no_image']:
            cid = card.get('cid')
            if cid:
                image_path = os.path.join(IMAGES_DIR, f"{cid}.jpg")
                if os.path.exists(image_path):
                    return False

        # Filtro por nombre
        query = self.search_entry.get_text().strip().lower()
        if query and query not in card.get('name', '').lower():
            return False

        if f['main_types']:
            if attr == 'SPELL' and 'spell' not in f['main_types']:
                return False
            elif attr == 'TRAP' and 'trap' not in f['main_types']:
                return False
            elif attr not in ('SPELL', 'TRAP') and 'monster' not in f['main_types']:
                return False

        if f['attributes'] and attr not in ('SPELL', 'TRAP') and attr not in f['attributes']:
            return False

        if f['subtypes']:
            type_str = card.get('type', '').lower()
            if not any(st.lower() in type_str for st in f['subtypes']):
                return False

        for key, card_key in (('level', 'level'), ('atk', 'atk'), ('def', 'def')):
            val = card.get(card_key)
            if val is not None:
                if f[f'{key}_min'] is not None and val < f[f'{key}_min']:
                    return False
                if f[f'{key}_max'] is not None and val > f[f'{key}_max']:
                    return False

        return True

    def _has_active_filters(self):
        f = self.active_filters
        return bool(
            f['main_types'] or f['attributes'] or f['subtypes'] or f['no_image'] or
            any(f[k] is not None for k in (
                'level_min', 'level_max', 'atk_min', 'atk_max', 'def_min', 'def_max',
            ))
        )

    def _update_filter_button(self):
        if self._has_active_filters():
            self.filter_btn.add_css_class('suggested-action')
        else:
            self.filter_btn.remove_css_class('suggested-action')

    def _clear_filters(self, _widget=None):
        if hasattr(self, 'filter_no_img_btn'):
            self.filter_no_img_btn.set_active(False)
        for btn in list(self.filter_type_btns.values()) + \
                   list(self.filter_attr_btns.values()) + \
                   list(self.filter_subtype_btns.values()):
            btn.set_active(False)
        for key in ('level', 'atk', 'def'):
            getattr(self, f"spin_{key}_min").set_value(getattr(self, f"spin_{key}_min_default"))
            getattr(self, f"spin_{key}_max").set_value(getattr(self, f"spin_{key}_max_default"))

    # ── Info panel ────────────────────────────────────────────────────────────

    def _build_info_panel(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer.add_css_class("background")

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        outer.append(sep)

        self.info_scrolled = Gtk.ScrolledWindow()
        self.info_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.info_scrolled.set_vexpand(True)
        self.info_scrolled.set_size_request(260, -1)
        outer.append(self.info_scrolled)

        self.info_scrolled.set_child(self._build_info_content())
        return outer

    def _build_info_content(self):
        SUBTYPE_KEYWORDS = [
            'Normal', 'Effect', 'Fusion', 'Ritual', 'Synchro',
            'XYZ', 'Pendulum', 'Link', 'Flip', 'Toon', 'Spirit',
            'Union', 'Gemini', 'Tuner',
        ]

        monsters = spells = traps = 0
        attributes: dict[str, int] = {}
        subtypes: dict[str, int] = {}

        for card in self.cards:
            attr = card.get('attribute', '')
            if attr == 'SPELL':
                spells += 1
            elif attr == 'TRAP':
                traps += 1
            else:
                monsters += 1
                if attr:
                    attributes[attr] = attributes.get(attr, 0) + 1

            type_str = card.get('type', '')
            for kw in SUBTYPE_KEYWORDS:
                if kw.lower() in type_str.lower():
                    subtypes[kw] = subtypes.get(kw, 0) + 1

        cached = 0
        if os.path.exists(IMAGES_DIR):
            cached = sum(1 for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg'))

        total = len(self.cards)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(12)
        content.set_margin_end(12)

        content.append(self._stat_group("Colección", [
            ("Total de cartas", str(total)),
            ("Monstruos", str(monsters)),
            ("Magias", str(spells)),
            ("Trampas", str(traps)),
            ("Imágenes cacheadas", f"{cached} / {total}"),
        ]))

        if attributes:
            content.append(self._stat_group(
                "Monstruos por Atributo",
                sorted(attributes.items(), key=lambda x: -x[1])
            ))

        if subtypes:
            content.append(self._stat_group(
                "Por Subtipo",
                sorted(subtypes.items(), key=lambda x: -x[1])
            ))

        return content

    def _refresh_info_panel(self):
        self.info_scrolled.set_child(self._build_info_content())

    def _stat_group(self, title, rows):
        group = Adw.PreferencesGroup(title=title)
        lb = Gtk.ListBox()
        lb.add_css_class("boxed-list")
        lb.set_selection_mode(Gtk.SelectionMode.NONE)
        for key, val in rows:
            r = Adw.ActionRow(title=str(key))
            lbl = Gtk.Label(label=str(val))
            lbl.add_css_class("dim-label")
            r.add_suffix(lbl)
            lb.append(r)
        group.add(lb)
        return group

    def _on_close(self, *_):
        w, h = self.get_width(), self.get_height()
        _save_settings({"width": w, "height": h})
        return False  # permite que la ventana se cierre normalmente

    def on_info_toggled(self, btn):
        self.info_revealer.set_reveal_child(btn.get_active())
        if btn.get_active():
            self._refresh_info_panel()

    # ── Card selection ────────────────────────────────────────────────────────

    def _make_stat_row_reusable(self, icon_name, label, value):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_top(3)
        row.set_margin_bottom(3)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        icon.add_css_class("dim-label")
        lbl = Gtk.Label(label=label)
        lbl.add_css_class("dim-label")
        lbl.set_halign(Gtk.Align.START)
        val_lbl = Gtk.Label(label=str(value))
        val_lbl.set_selectable(True)
        val_lbl.set_hexpand(True)
        val_lbl.set_halign(Gtk.Align.END)
        val_lbl.set_wrap(True)
        row.append(icon)
        row.append(lbl)
        row.append(val_lbl)
        return row, val_lbl

    def _load_image_async(self, image_path, cid):
        try:
            from gi.repository import Gdk
            texture = Gdk.Texture.new_from_filename(image_path)
            GLib.idle_add(self._set_image, texture, cid)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")

    def _set_image(self, texture, cid):
        if self._current_cid == cid:
            self.card_image.set_paintable(texture)
        return False

    def _make_stat_row(self, icon_name, label, value):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_top(3)
        row.set_margin_bottom(3)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        icon.add_css_class("dim-label")

        lbl = Gtk.Label(label=label)
        lbl.add_css_class("dim-label")
        lbl.set_halign(Gtk.Align.START)

        val_lbl = Gtk.Label(label=str(value))
        val_lbl.set_selectable(True)
        val_lbl.set_hexpand(True)
        val_lbl.set_halign(Gtk.Align.END)
        val_lbl.set_wrap(True)

        row.append(icon)
        row.append(lbl)
        row.append(val_lbl)
        return row

    def on_row_selected(self, listbox, row):
        if not row:
            return

        card = row.card_data
        self.name_label.set_text(card.get('name', 'Unknown'))
        self.desc_label.set_text(card.get('text', 'No description available.'))

        def _fmt(val):
            return str(val) if val is not None else '-'

        for val_lbl, value in zip(self._stat_val_labels, [
            card.get('attribute', '-'),
            _fmt(card.get('level')),
            card.get('type') or '-',
            _fmt(card.get('atk')),
            _fmt(card.get('def')),
        ]):
            val_lbl.set_text(str(value))

        cid = card.get('cid')
        image_url = card.get('image_url')
        self._current_cid = cid
        self.card_image.set_paintable(None)
        if cid:
            image_path = os.path.join(IMAGES_DIR, f"{cid}.jpg")
            if os.path.exists(image_path):
                self.status_label.set_text("")
                self.executor.submit(self._load_image_async, image_path, cid)
            else:
                if cid not in self.downloading_cids:
                    self.downloading_cids.add(cid)
                    self.queue_count += 1
                    self.update_status_ui()
                    self.executor.submit(self.download_image, image_url, image_path, cid)
                else:
                    self.update_status_ui()

        if self.info_revealer.get_reveal_child():
            self._refresh_info_panel()

    # ── Background Profile Downloader ─────────────────────────────────────────

    def start_bg_download(self, btn):
        if self.bg_download_running:
            self._show_toast_idle("Ya hay una descarga secuencial ejecutándose.")
            return
        self.bg_download_running = True
        self.bg_download_cancelled = False
        self.bg_download_thread = threading.Thread(target=self._bg_download_task, daemon=True)
        self.bg_download_thread.start()
        self._show_toast_idle("Descarga de bajo perfil iniciada.")

    def show_download_status(self, btn):
        missing = 0
        downloaded = 0
        for card in self.cards:
            cid = card.get('cid')
            if cid:
                if os.path.exists(os.path.join(IMAGES_DIR, f"{cid}.jpg")):
                    downloaded += 1
                else:
                    missing += 1
                    
        total = missing + downloaded
        state = "Corriendo" if self.bg_download_running else "Detenido"
        msg = f"Estado: {state}\nTotal: {total}\nDescargadas: {downloaded}\nFaltantes: {missing}"
        
        dlg = Adw.MessageDialog(heading="Estado de Descargas", body=msg)
        dlg.add_response("ok", "Aceptar")
        if self.bg_download_running:
            dlg.add_response("cancel", "Detener Descarga")
            dlg.set_response_appearance("cancel", Adw.ResponseAppearance.DESTRUCTIVE)
            
        dlg.connect("response", self._on_status_dlg_response)
        dlg.set_transient_for(self)
        dlg.present()
        
    def _on_status_dlg_response(self, dlg, response):
        if response == "cancel":
            self.bg_download_cancelled = True
            
    def _show_toast_idle(self, text):
        self.toast_overlay.add_toast(Adw.Toast(title=text))
        return False
        
    def _add_to_bg_queue(self, cid):
        if cid not in self.downloading_cids:
            self.downloading_cids.add(cid)
            self.queue_count += 1
            self.update_status_ui()
        return False

    def _bg_download_task(self):
        missing_cids = []
        for card in self.cards:
            cid = card.get('cid')
            if cid and not os.path.exists(os.path.join(IMAGES_DIR, f"{cid}.jpg")):
                missing_cids.append(card)

        for card in missing_cids:
            if self.bg_download_cancelled:
                break
            
            cid = card.get('cid')
            image_url = card.get('image_url')
            image_path = os.path.join(IMAGES_DIR, f"{cid}.jpg")
            
            GLib.idle_add(self._add_to_bg_queue, cid)
            
            # This is fully synchronous in this background thread
            self.download_image(image_url, image_path, cid)
            
            time.sleep(random.uniform(1.0, 3.0))

        self.bg_download_running = False
        msg = "Descarga de bajo perfil detenida." if self.bg_download_cancelled else "Descargas completadas exitosamente."
        GLib.idle_add(self._show_toast_idle, msg)

    # ── Image download ────────────────────────────────────────────────────────

    def update_status_ui(self):
        if self.queue_count > 0:
            active = min(self.queue_count, 5)
            queued = max(0, self.queue_count - 5)
            text = f"Descargando {active} imagen(es)..."
            if queued:
                text += f" ({queued} en cola)"
            self.status_label.set_text(text)
        else:
            self.status_label.set_text("")

    def download_image(self, url, filepath, cid):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

            if not url or "get_image.action" in url:
                detail_url = f"https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=2&cid={cid}"
                req = urllib.request.Request(detail_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    html = response.read().decode('utf-8', errors='replace')
                match = re.search(
                    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
                    html
                )
                if match:
                    url = match.group(1)

            if url:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    with open(filepath, 'wb') as f:
                        f.write(response.read())

            GLib.idle_add(self.image_downloaded, filepath, cid)
        except Exception as e:
            print(f"Error downloading image for cid {cid}: {e}")
            GLib.idle_add(self.image_download_failed, cid)

    def image_downloaded(self, filepath, cid):
        if cid in self.downloading_cids:
            self.downloading_cids.remove(cid)
            self.queue_count -= 1
        self.update_status_ui()
        row = self.listbox.get_selected_row()
        if row and row.card_data.get('cid') == cid:
            self.card_image.set_filename(filepath)
        if self.info_revealer.get_reveal_child():
            self._refresh_info_panel()

    def image_download_failed(self, cid):
        if cid in self.downloading_cids:
            self.downloading_cids.remove(cid)
            self.queue_count -= 1
        self.update_status_ui()


class YgoApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.YgoViewer",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        db = DatabaseManager(DB_FILE)
        db.init_db()
        cards = db.get_cards()

        win = self.props.active_window
        if not win:
            win = YgoViewerWindow(self, cards)
        win.present()


if __name__ == "__main__":
    app = YgoApp()
    app.run(None)
