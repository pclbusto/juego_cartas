import arcade
import constants
from database import DatabaseManager
import os
from collections import OrderedDict

# ── Layout ────────────────────────────────────────────────────────────────────
SW = constants.SCREEN_WIDTH   # 1280
SH = constants.SCREEN_HEIGHT  # 720
CW = constants.CARD_WIDTH     # 90
CH = constants.CARD_HEIGHT    # 130

TOOLBAR_H  = 50
SEARCH_H   = 55
DECK_H     = 210
DETAIL_W   = 290
PAD        = 10
CARD_GAP_X = 12
CARD_GAP_Y = 5

AVAIL_W    = SW - DETAIL_W        # 990
AVAIL_YTOP = SH - TOOLBAR_H - SEARCH_H  # 615
AVAIL_YBOT = DECK_H               # 210
CARD_STEP  = CW + CARD_GAP_X     # 102
COLS       = (AVAIL_W - PAD * 2) // CARD_STEP  # 9

DECK_CARD_Y  = 107   # center y for deck card sprites
DECK_STATS_Y = 27    # y of thin stats bar text

# ── Colors ────────────────────────────────────────────────────────────────────
BG        = (26, 26, 26)
PANEL     = (38, 38, 38)
DECK_BG   = (44, 44, 44)
DETAIL_BG = (33, 33, 33)
SEP       = (60, 60, 60)
TEXT      = (225, 225, 225)
DIM       = (120, 120, 120)
GOLD      = (255, 200, 50)
BLUE      = (30, 130, 255)
RED       = (210, 60, 60)
GREEN     = (50, 190, 80)
BTN_ACT   = (40, 100, 200)
BTN       = (55, 55, 55)
BTN_HOV   = (70, 70, 70)
C_MONSTER = (220, 120, 50)
C_SPELL   = (100, 200, 255)
C_TRAP    = (210, 100, 100)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _in_rect(x, y, x1, y1, x2, y2):
    return x1 <= x <= x2 and y1 <= y <= y2


def _rrect_filled(x1, y1, x2, y2, r, color):
    """Filled rounded rectangle."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    arcade.draw_lrbt_rectangle_filled(x1 + r, x2 - r, y1, y2, color)
    arcade.draw_lrbt_rectangle_filled(x1, x2, y1 + r, y2 - r, color)
    for cx, cy in [(x1+r, y1+r), (x2-r, y1+r), (x1+r, y2-r), (x2-r, y2-r)]:
        arcade.draw_circle_filled(cx, cy, r, color)


def _rrect_outline(x1, y1, x2, y2, r, color, lw=1):
    """Rounded rectangle outline using lines + arc segments."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    arcade.draw_line(x1 + r, y1,  x2 - r, y1,  color, lw)   # bottom
    arcade.draw_line(x1 + r, y2,  x2 - r, y2,  color, lw)   # top
    arcade.draw_line(x1, y1 + r,  x1, y2 - r,  color, lw)   # left
    arcade.draw_line(x2, y1 + r,  x2, y2 - r,  color, lw)   # right
    d = r * 2
    arcade.draw_arc_outline(x1+r, y1+r, d, d, color, 180, 270, lw)  # BL
    arcade.draw_arc_outline(x2-r, y1+r, d, d, color, 270, 360, lw)  # BR
    arcade.draw_arc_outline(x2-r, y2-r, d, d, color,   0,  90, lw)  # TR
    arcade.draw_arc_outline(x1+r, y2-r, d, d, color,  90, 180, lw)  # TL


def _neon_glow(x1, y1, x2, y2, color, r=8, alpha_mult=1.0):
    """Neon tube effect: soft bloom rings + bright border + white plasma core."""
    # Outer bloom — many transparent expanding rings
    for i in range(14, 0, -1):
        exp   = i * 3.5
        alpha = int(min(8 + i * 9, 170) * alpha_mult)
        if alpha > 0:
            ri    = r + exp * 0.35
            _rrect_outline(x1 - exp, y1 - exp, x2 + exp, y2 + exp,
                           ri, (*color, alpha), 2)
    # Colored glass tube border
    if alpha_mult > 0:
        _rrect_outline(x1, y1, x2, y2, r, (*color, int(255 * alpha_mult)), 2)
        # White plasma core (hot center of the neon tube)
        _rrect_outline(x1, y1, x2, y2, r, (255, 255, 255, int(140 * alpha_mult)), 1)


def _draw_btn(cx, cy, w, h, label, hovered=False, active=False):
    x1, x2 = cx - w // 2, cx + w // 2
    y1, y2 = cy - h // 2, cy + h // 2
    bg = BTN_ACT if active else (BTN_HOV if hovered else BTN)
    _rrect_filled(x1, y1, x2, y2, 7, bg)
    border = (*BLUE, 180) if active else (*SEP, 120)
    _rrect_outline(x1, y1, x2, y2, 7, border, 1)
    arcade.draw_text(label, cx, cy, TEXT, font_size=11,
                     anchor_x="center", anchor_y="center")


# ── Card sprite ───────────────────────────────────────────────────────────────

class CardSprite(arcade.Sprite):
    def __init__(self, card_data, x, y, texture=None):
        super().__init__()
        if texture is not None:
            self.texture = texture
        else:
            import PIL.Image
            from arcade import Texture
            img = PIL.Image.new('RGBA', (CW, CH), (55, 55, 72, 255))
            self.texture = Texture(img)
        self._card_scale = 1.0
        self.scale = 1.0

        self.card_data = card_data
        self._base_x   = x
        self._base_y   = y
        self.center_x  = x
        self.center_y  = y
        self._qty      = 1
        self.anim_progress = 0.0

    def update_animation(self, delta_time, is_hovered):
        target = 1.0 if is_hovered else 0.0
        speed = min(1.0, 15.0 * delta_time)
        self.anim_progress += (target - self.anim_progress) * speed
        
        if abs(self.anim_progress - target) < 0.01:
            self.anim_progress = target
            
        # Adicionalmente clampamos por seguridad
        self.anim_progress = max(0.0, min(1.0, self.anim_progress))
            
        SCALE_UP = 1.18
        LIFT = 14.0
        
        current_scale_mult = 1.0 + (SCALE_UP - 1.0) * self.anim_progress
        self.scale = self._card_scale * current_scale_mult
        self.center_y = self._base_y + LIFT * self.anim_progress

    def draw_glow(self, color, label):
        if self.anim_progress <= 0.01:
            return

        alpha = int(220 * self.anim_progress)
        
        cx = self.center_x
        cy = self.center_y

        # Action badge (solo mantenemos el pequeño círculo indicador de +/- en el centro)
        arcade.draw_circle_filled(cx, cy, 15, (*color, alpha))
        arcade.draw_text(label, cx, cy, (255, 255, 255, int(255 * self.anim_progress)),
                         font_size=18, bold=True,
                         anchor_x="center", anchor_y="center")

    def draw_qty_badge(self, qty):
        bx = self.center_x + CW / 2 - 11
        by = self.center_y + CH / 2 - 11
        arcade.draw_circle_filled(bx, by, 12, (15, 15, 15))
        arcade.draw_circle_outline(bx, by, 12, GOLD, 1.5)
        arcade.draw_text(str(qty), bx, by, GOLD, font_size=10, bold=True,
                         anchor_x="center", anchor_y="center")


# ── View ──────────────────────────────────────────────────────────────────────

class DeckBuilderView(arcade.View):

    def __init__(self):
        super().__init__()
        # SpriteLists are created in setup() with a dedicated high-capacity atlas
        self.avail_sprites    = arcade.SpriteList()
        self.deck_sprites     = arcade.SpriteList()
        self._card_atlas      = None
        self.db               = None
        self.all_cards        = []
        self.current_deck_id   = None
        self.current_deck_name = ""
        self.deck_cards_data   = []
        self.avail_scroll      = 0
        self.deck_scroll       = 0
        self.search_text       = ""
        self.search_active     = False
        self.type_filter       = "ALL"
        self.hover_sprite      = None
        self.hover_in_deck     = False
        self.detail_card       = None
        self._tex_cache        = OrderedDict()  # LRU: move_to_end on hit, popitem(last=False) on evict
        self._THUMB_LIMIT      = None  # set from DB in setup()
        self._DETAIL_LIMIT     = 20
        self._free_on_exit     = False  # set from DB in setup()
        self.mx = self.my      = 0

    def setup(self):
        # Dedicated atlas: capacity=4 → 16 384 UV slots; auto_resize handles pixel growth
        from arcade.texture_atlas import DefaultTextureAtlas
        self._card_atlas  = DefaultTextureAtlas((2048, 2048), capacity=4)
        self.avail_sprites = arcade.SpriteList(atlas=self._card_atlas)
        self.deck_sprites  = arcade.SpriteList(atlas=self._card_atlas)

        self.db = DatabaseManager()
        self.db.init_db()

        # Load settings
        raw_limit = self.db.get_setting("thumb_limit", None)
        self._THUMB_LIMIT  = int(raw_limit) if raw_limit is not None else None
        self._free_on_exit = self.db.get_setting("free_on_exit", "0") == "1"

        self.all_cards = self.db.get_cards()

        decks = self.db.get_all_decks()
        if decks:
            self.current_deck_id   = decks[0]['id']
            self.current_deck_name = decks[0]['name']
        else:
            self.current_deck_id   = self.db.create_deck("Mi Primer Deck")
            self.current_deck_name = "Mi Primer Deck"

        self.load_deck()
        self.update_avail_display()
        self.update_deck_display()

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_deck(self):
        self.deck_cards_data = (
            self.db.get_deck_cards(self.current_deck_id)
            if self.current_deck_id else []
        )

    def get_filtered(self):
        q = self.search_text.lower()
        result = []
        for c in self.all_cards:
            if q and q not in c.get('name', '').lower():
                continue
            ct = c.get('card_type', '')
            if self.type_filter == 'MONSTER' and ct != 'MONSTER':
                continue
            if self.type_filter == 'SPELL' and ct != 'SPELL':
                continue
            if self.type_filter == 'TRAP' and ct != 'TRAP':
                continue
            if self.type_filter == 'NO_IMG':
                path = f"images/{c.get('image_name', '')}"
                if os.path.exists(path):
                    continue
            result.append(c)
        return result

    def get_deck_stats(self):
        monsters = spells = traps = 0
        for c in self.deck_cards_data:
            qty = c.get('quantity', 1)
            ct  = c.get('card_type', '')
            if ct == 'MONSTER':   monsters += qty
            elif ct == 'SPELL':   spells   += qty
            elif ct == 'TRAP':    traps    += qty
        return {'monsters': monsters, 'spells': spells,
                'traps': traps, 'total': monsters + spells + traps}

    # ── Display refresh ───────────────────────────────────────────────────────

    def _recalc_hover(self):
        self.on_mouse_motion(self.mx, self.my, 0, 0)

    def update_avail_display(self):
        self.avail_sprites.clear()
        filtered = self.get_filtered()
        start    = self.avail_scroll * COLS

        # Row positions: 3 rows max, skipping any that overlap deck strip
        row_y0 = AVAIL_YTOP - CH // 2 - 5  # 545

        for idx, card in enumerate(filtered[start: start + COLS * 3]):
            row = idx // COLS
            col = idx % COLS
            cy  = row_y0 - row * (CH + CARD_GAP_Y)
            if cy - CH // 2 < AVAIL_YBOT:
                continue
            cx = PAD + CW // 2 + col * CARD_STEP
            tex = self._get_thumb(card.get('image_name'))
            self.avail_sprites.append(CardSprite(card, cx, cy, texture=tex))
        self._recalc_hover()

    def update_deck_display(self):
        self.deck_sprites.clear()
        stats_w  = 360
        max_cols = (AVAIL_W - stats_w - PAD) // CARD_STEP

        for idx, card in enumerate(
            self.deck_cards_data[self.deck_scroll: self.deck_scroll + max_cols]
        ):
            cx = stats_w + CW // 2 + idx * CARD_STEP
            tex = self._get_thumb(card.get('image_name'))
            s  = CardSprite(card, cx, DECK_CARD_Y, texture=tex)
            s._qty = card.get('quantity', 1)
            self.deck_sprites.append(s)
        self._recalc_hover()

    def _get_thumb(self, image_name):
        """Card-sized texture (CW×CH) for sprite grid — LRU capped at _THUMB_LIMIT."""
        if not image_name:
            return None
        key = f"thumb:{image_name}"
        if key in self._tex_cache:
            self._tex_cache.move_to_end(key)  # mark as recently used
            return self._tex_cache[key]
        path = f"images/{image_name}"
        if os.path.exists(path):
            try:
                import PIL.Image
                from arcade import Texture
                img = PIL.Image.open(path).convert('RGBA').resize(
                    (CW, CH), PIL.Image.LANCZOS)
                tex = Texture(img)
                self._tex_cache[key] = tex
                self._evict_thumbs()
                return tex
            except Exception:
                pass
        return None

    def _evict_thumbs(self):
        """Remove oldest thumbnails when over the limit. No-op when limit is None."""
        if self._THUMB_LIMIT is None:
            return
        thumb_keys = [k for k in self._tex_cache if k.startswith("thumb:")]
        while len(thumb_keys) > self._THUMB_LIMIT:
            oldest_key = next(k for k in self._tex_cache if k.startswith("thumb:"))
            tex = self._tex_cache.pop(oldest_key)
            try:
                self._card_atlas.remove(tex)
            except Exception:
                pass
            thumb_keys.pop(0)

    def _release_atlas(self):
        """Free all cached textures and release the GPU atlas immediately."""
        self.avail_sprites.clear()
        self.deck_sprites.clear()
        self._tex_cache.clear()
        self._card_atlas = None

    def _get_tex(self, image_name):
        """Full-size texture for the detail panel — LRU capped at _DETAIL_LIMIT."""
        if not image_name:
            return None
        key = f"full:{image_name}"
        if key in self._tex_cache:
            self._tex_cache.move_to_end(key)
            return self._tex_cache[key]
        path = f"images/{image_name}"
        if os.path.exists(path):
            try:
                tex = arcade.load_texture(path)
                self._tex_cache[key] = tex
                # evict oldest full-size textures
                full_keys = [k for k in self._tex_cache if k.startswith("full:")]
                while len(full_keys) > self._DETAIL_LIMIT:
                    oldest = next(k for k in self._tex_cache if k.startswith("full:"))
                    self._tex_cache.pop(oldest)
                    full_keys.pop(0)
                return tex
            except Exception:
                pass
        return None

    # ── Draw ──────────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear()

        # ── Panels ──
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG)
        arcade.draw_lrbt_rectangle_filled(0, SW, SH - TOOLBAR_H, SH, PANEL)
        arcade.draw_line(0, SH - TOOLBAR_H, SW, SH - TOOLBAR_H, SEP, 1)

        arcade.draw_lrbt_rectangle_filled(0, AVAIL_W, DECK_H, SH - TOOLBAR_H, PANEL)
        arcade.draw_line(0, AVAIL_YTOP, AVAIL_W, AVAIL_YTOP, SEP, 1)

        # Detail panel extends full height so description isn't clipped
        arcade.draw_lrbt_rectangle_filled(AVAIL_W, SW, 0, SH - TOOLBAR_H, DETAIL_BG)
        arcade.draw_line(AVAIL_W, 0, AVAIL_W, SH - TOOLBAR_H, SEP, 1)

        # Deck strip only on the left side
        arcade.draw_lrbt_rectangle_filled(0, AVAIL_W, 0, DECK_H, DECK_BG)
        arcade.draw_line(0, DECK_H, AVAIL_W, DECK_H, SEP, 1)

        # thin stats bar at very bottom of deck strip
        arcade.draw_lrbt_rectangle_filled(0, AVAIL_W, 0, 30, (30, 30, 30))
        arcade.draw_line(0, 30, AVAIL_W, 30, SEP, 1)

        # ── Toolbar ──
        arcade.draw_text(f"  {self.current_deck_name}",
                         20, SH - TOOLBAR_H + 14, GOLD, font_size=16, bold=True)
        tby = SH - TOOLBAR_H // 2  # 695
        for cx, lbl in self._toolbar_btns():
            hov = _in_rect(self.mx, self.my, cx - 55, tby - 16, cx + 55, tby + 16)
            _draw_btn(cx, tby, 110, 32, lbl, hovered=hov)

        # ── Search area ──
        sx, sy = PAD, AVAIL_YTOP + 12
        sbw, sbh = 280, 32
        border = BLUE if self.search_active else SEP
        _rrect_filled(sx, sy, sx + sbw, sy + sbh, 8, (48, 48, 48))
        _rrect_outline(sx, sy, sx + sbw, sy + sbh, 8, border, 1.5)
        placeholder = not bool(self.search_text)
        disp = ("Buscar por nombre..." if placeholder
                else self.search_text + ("_" if self.search_active else ""))
        arcade.draw_text(disp, sx + 10, sy + sbh // 2,
                         DIM if placeholder else TEXT,
                         font_size=11, anchor_y="center")

        # Type filter pills
        fx = sx + sbw + 16
        for code, lbl, w in [("ALL", "Todos", 68), ("MONSTER", "Monstruo", 90),
                               ("SPELL", "Magia", 72), ("TRAP", "Trampa", 72),
                               ("NO_IMG", "Sin Imagen", 90)]:
            active = self.type_filter == code
            hov    = _in_rect(self.mx, self.my, fx, sy, fx + w, sy + sbh)
            _draw_btn(fx + w // 2, sy + sbh // 2, w, sbh, lbl,
                      hovered=hov, active=active)
            fx += w + 8

        arcade.draw_text("Cartas Disponibles", PAD, AVAIL_YTOP - 13,
                         DIM, font_size=11)

        # Scroll hint
        filtered   = self.get_filtered()
        total_rows = (len(filtered) + COLS - 1) // COLS
        rows_vis   = 3
        if total_rows > rows_vis:
            arcade.draw_text(
                f"Pág. {self.avail_scroll + 1}/{max(1, total_rows - rows_vis + 1)}"
                "  (rueda para navegar)",
                AVAIL_W // 2, AVAIL_YBOT + 5, DIM, font_size=9, anchor_x="center"
            )

        # ── Available cards ──
        self.avail_sprites.draw()
        for s in self.avail_sprites:
            s.draw_glow(BLUE, "+")

        # ── Detail panel ──
        self._draw_detail()

        # ── Deck strip ──
        stats = self.get_deck_stats()
        arcade.draw_text("DECK ACTUAL",
                         PAD, DECK_H - 14, DIM, font_size=9, bold=True)

        # Colored stat badges
        bh, br = 22, 11
        by1, by2 = DECK_STATS_Y - 1, DECK_STATS_Y + bh - 1
        bx = PAD
        total_col = (GREEN if 40 <= stats['total'] <= 60
                     else RED if stats['total'] > 60 else GOLD)
        for txt, fg, bg_dark in [
            (f"♟ {stats['monsters']} Monstruos", C_MONSTER, (55, 28, 5)),
            (f"✦ {stats['spells']} Magias",      C_SPELL,   (5, 30, 60)),
            (f"⚠ {stats['traps']} Trampas",      C_TRAP,    (55, 10, 10)),
            (f"◈ {stats['total']}/60",           total_col, (20, 20, 20)),
        ]:
            tw = len(txt) * 7 + 18
            _rrect_filled(bx, by1, bx + tw, by2, br, bg_dark)
            _rrect_outline(bx, by1, bx + tw, by2, br, (*fg, 160), 1)
            arcade.draw_text(txt, bx + tw // 2, DECK_STATS_Y + bh // 2,
                             fg, font_size=10,
                             anchor_x="center", anchor_y="center")
            bx += tw + 8

        self.deck_sprites.draw()
        for s in self.deck_sprites:
            s.draw_glow(RED, "−")
            s.draw_qty_badge(s._qty)

    def _draw_detail(self):
        dpx = AVAIL_W + DETAIL_W // 2  # 1135

        if not self.detail_card:
            arcade.draw_text(
                "Pasa el cursor\nsobre una carta\npara ver detalles",
                dpx, (SH - TOOLBAR_H + DECK_H) // 2,
                DIM, font_size=12, anchor_x="center", anchor_y="center",
                multiline=True, width=DETAIL_W - 20, align="center"
            )
            return

        card    = self.detail_card
        tex     = self._get_tex(card.get('image_name'))
        img_h   = 245
        img_y   = SH - TOOLBAR_H - img_h // 2 - 8  # 539

        if tex:
            scale = min((DETAIL_W - 24) / tex.width, img_h / tex.height)
            s = arcade.Sprite()
            s.texture  = tex
            s.scale    = scale
            s.center_x = dpx
            s.center_y = img_y
            sl = arcade.SpriteList()
            sl.append(s)
            sl.draw()
        else:
            arcade.draw_lrbt_rectangle_filled(
                AVAIL_W + 12, SW - 12,
                img_y - img_h // 2, img_y + img_h // 2,
                (55, 55, 72)
            )

        # Name — with subtle background
        ny  = img_y - img_h // 2 - 8
        pad = 12
        _rrect_filled(AVAIL_W + 6, ny - 38, SW - 6, ny + 2, 8, (42, 42, 42))
        arcade.draw_text(card.get('name', '?'),
                         AVAIL_W + pad, ny, TEXT,
                         font_size=13, bold=True,
                         width=DETAIL_W - pad * 2, multiline=True, anchor_y="top")

        # Stats rows with icon-like prefix symbols
        def _fmt(v): return str(v) if v is not None else '?'
        attr  = card.get('attribute', '')
        ctype = card.get('card_type', '')
        # Attribute color
        attr_col = {'DARK': (160, 80, 200), 'LIGHT': (240, 230, 80),
                    'FIRE': (240, 100, 40), 'WATER': (60, 160, 230),
                    'EARTH': (140, 110, 60), 'WIND': (80, 200, 120),
                    'DIVINE': (240, 200, 80)}.get(attr, TEXT)

        sy = ny - 52
        rows = []
        if ctype == 'MONSTER':
            rows = [
                ("⬡ Atributo", attr or '-', attr_col),
                ("★ Nivel",    _fmt(card.get('level')), GOLD),
                ("⚔ ATK",      _fmt(card.get('atk')),  (200, 80, 80)),
                ("🛡 DEF",      _fmt(card.get('def')),  (80, 150, 220)),
                ("◉ Tipo",     (card.get('type') or '-')[:28], DIM),
            ]
        elif ctype == 'SPELL':
            rows = [
                ("✦ Tipo",     (card.get('type') or 'Normal')[:28], C_SPELL),
            ]
        elif ctype == 'TRAP':
            rows = [
                ("⚠ Tipo",     (card.get('type') or 'Normal')[:28], C_TRAP),
            ]

        for icon_label, val, val_col in rows:
            arcade.draw_text(icon_label, AVAIL_W + pad, sy, DIM, font_size=10)
            arcade.draw_text(val, SW - pad, sy, val_col,
                             font_size=10, bold=True, anchor_x="right")
            sy -= 20

        # Separator
        arcade.draw_line(AVAIL_W + pad, sy - 4, SW - pad, sy - 4, SEP, 1)

        # Effect text
        effect = card.get('text', '')
        if effect:
            arcade.draw_text(
                effect, AVAIL_W + pad, sy - 12,
                (175, 175, 175), font_size=9,
                width=DETAIL_W - pad * 2, multiline=True, anchor_y="top"
            )

    # ── Events ────────────────────────────────────────────────────────────────

    def _toolbar_btns(self):
        return [
            (SW - 75,  "← Atrás"),
            (SW - 200, "✓ Guardar"),
            (SW - 325, "+ Nuevo Deck"),
        ]

    def on_update(self, delta_time):
        for s in self.avail_sprites:
            is_hovered = (s is self.hover_sprite and not self.hover_in_deck)
            s.update_animation(delta_time, is_hovered)
            
        for s in self.deck_sprites:
            is_hovered = (s is self.hover_sprite and self.hover_in_deck)
            s.update_animation(delta_time, is_hovered)

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y
        av = arcade.get_sprites_at_point((x, y), self.avail_sprites)
        dk = arcade.get_sprites_at_point((x, y), self.deck_sprites)
        if av:
            target = av[-1]
            if self.hover_sprite != target:
                self.hover_sprite = target
                if target in self.avail_sprites:
                    self.avail_sprites.remove(target)
                    self.avail_sprites.append(target)
            self.hover_in_deck = False
            self.detail_card   = target.card_data
        elif dk:
            target = dk[-1]
            if self.hover_sprite != target:
                self.hover_sprite = target
                if target in self.deck_sprites:
                    self.deck_sprites.remove(target)
                    self.deck_sprites.append(target)
            self.hover_in_deck = True
            self.detail_card   = target.card_data
        else:
            self.hover_sprite = None

    def on_mouse_press(self, x, y, button, modifiers):
        # Toolbar
        tby = SH - TOOLBAR_H // 2
        for cx, lbl in self._toolbar_btns():
            if _in_rect(x, y, cx - 55, tby - 16, cx + 55, tby + 16):
                if "Atrás"   in lbl: self._go_back()
                elif "Guardar" in lbl: self._save_deck()
                elif "Nuevo"  in lbl: self._new_deck()
                return

        # Search box focus
        sx, sy = PAD, AVAIL_YTOP + 12
        if _in_rect(x, y, sx, sy, sx + 280, sy + 32):
            self.search_active = True
            return
        self.search_active = False

        # Type filter pills
        fx = sx + 280 + 16
        for code, _, w in [("ALL", "", 68), ("MONSTER", "", 90),
                            ("SPELL", "", 72), ("TRAP", "", 72),
                            ("NO_IMG", "", 90)]:
            if _in_rect(x, y, fx, sy, fx + w, sy + 32):
                if self.type_filter != code:
                    self.type_filter  = code
                    self.avail_scroll = 0
                    self.update_avail_display()
                return
            fx += w + 8

        # Available cards — left click adds to deck
        av = arcade.get_sprites_at_point((x, y), self.avail_sprites)
        if av and button == arcade.MOUSE_BUTTON_LEFT and self.current_deck_id:
            if self.db.add_card_to_deck(self.current_deck_id,
                                        av[-1].card_data['cid']):
                self.load_deck()
                self.update_deck_display()
            return

        # Deck cards — left click removes one copy
        dk = arcade.get_sprites_at_point((x, y), self.deck_sprites)
        if dk and button == arcade.MOUSE_BUTTON_LEFT and self.current_deck_id:
            self.db.remove_card_from_deck(self.current_deck_id,
                                          dk[-1].card_data['cid'])
            self.load_deck()
            self.update_deck_display()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if _in_rect(x, y, 0, AVAIL_YBOT, AVAIL_W, SH - TOOLBAR_H):
            filtered   = self.get_filtered()
            total_rows = (len(filtered) + COLS - 1) // COLS
            max_scroll = max(0, total_rows - 3)
            delta = -1 if scroll_y > 0 else 1
            self.avail_scroll = max(0, min(max_scroll, self.avail_scroll + delta))
            self.update_avail_display()
        elif _in_rect(x, y, 0, 0, AVAIL_W, DECK_H):
            stats_w    = 360
            max_cols   = (AVAIL_W - stats_w - PAD) // CARD_STEP
            max_scroll = max(0, len(self.deck_cards_data) - max_cols)
            delta = -1 if (scroll_x > 0 or scroll_y < 0) else 1
            self.deck_scroll = max(0, min(max_scroll, self.deck_scroll + delta))
            self.update_deck_display()

    def on_text(self, text):
        if self.search_active:
            self.search_text += text
            self.avail_scroll = 0
            self.update_avail_display()

    def on_key_press(self, symbol, modifiers):
        if self.search_active:
            if symbol == arcade.key.BACKSPACE:
                self.search_text = self.search_text[:-1]
                self.avail_scroll = 0
                self.update_avail_display()
            elif symbol == arcade.key.ESCAPE:
                self.search_active = False
        elif symbol == arcade.key.ESCAPE:
            self._go_back()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _go_back(self):
        from game_view import GameView
        v = GameView()
        v.setup()
        self.window.show_view(v)

    def _save_deck(self):
        if self.current_deck_id:
            stats = self.get_deck_stats()
            print(f"[Deck] '{self.current_deck_name}' — {stats['total']} cartas")

    def _new_deck(self):
        n    = len(self.db.get_all_decks()) + 1
        name = f"Deck {n}"
        self.current_deck_id   = self.db.create_deck(name)
        self.current_deck_name = name
        self.deck_scroll       = 0
        self.load_deck()
        self.update_deck_display()

    def on_hide_view(self):
        if self._free_on_exit:
            self._release_atlas()
