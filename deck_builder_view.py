import arcade
import constants
from database import DatabaseManager
import os
from collections import OrderedDict
from ui_prueba_concepto import ShaderPanel, ShaderButton

# ── Layout ────────────────────────────────────────────────────────────────────
SW = constants.SCREEN_WIDTH   # 1280
SH = constants.SCREEN_HEIGHT  # 720
CW = 105     # 90 -> 105
CH = 150     # 130 -> 150

TOOLBAR_H  = 50
SEARCH_H   = 55
DECK_H     = 210
DETAIL_W   = 290
PAD        = 10
CARD_GAP_X = 12
CARD_GAP_Y = 5

PAD          = 15
TOP_BAR_H    = 60
BOTTOM_BAR_H = 40
DECK_PANEL_H = 326
DETAIL_W     = 340
STATS_W      = 360
LEFT_W       = SW - DETAIL_W - PAD * 3

P1_X1 = PAD
P1_Y2 = SH - TOP_BAR_H
P2_X1 = PAD
P2_Y1 = BOTTOM_BAR_H + PAD
P1_X2 = PAD + LEFT_W
P2_X2 = PAD + LEFT_W
P2_Y2 = P2_Y1 + DECK_PANEL_H
P1_Y1 = P2_Y2 + PAD

P3_X1 = P1_X2 + PAD
P3_Y1 = P2_Y1
P3_X2 = SW - PAD
P3_Y2 = P1_Y2

# ── Colors ────────────────────────────────────────────────────────────────────
BG            = (28, 28, 30)
PANEL_BG      = (38, 40, 44)
PANEL_OUTLINE = (60, 60, 65)
SEP           = (70, 70, 75)
TEXT          = (240, 240, 240)
DIM           = (150, 150, 150)
GOLD          = (255, 200, 50)
BLUE          = (30, 130, 255)
GREEN         = (50, 190, 80)
BTN           = (55, 55, 60)
BTN_HOV       = (75, 75, 80)
BTN_ACT       = (40, 100, 200)
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
        self.bottom_label = None # New attribute for bottom text

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
        # Usamos self.width/height reales para que el badge siga a la carta incluso escalada
        bx = self.center_x + self.width / 2 - 11
        by = self.center_y + self.height / 2 - 11
        arcade.draw_circle_filled(bx, by, 12, (15, 15, 15))
        arcade.draw_circle_outline(bx, by, 12, GOLD, 1.5)
        arcade.draw_text(str(qty), bx, by, GOLD, font_size=10, bold=True,
                         anchor_x="center", anchor_y="center")


# ── View ──────────────────────────────────────────────────────────────────────

class DeckBuilderView(arcade.View):

    def __init__(self, deck_id=None):
        super().__init__()
        # SpriteLists are created in setup() with a dedicated high-capacity atlas
        self.avail_sprites    = arcade.SpriteList()
        self.deck_sprites     = arcade.SpriteList()
        self._card_atlas      = None
        self.db               = None
        self.all_cards        = []
        self.current_deck_id   = deck_id
        self.current_deck_name = ""
        self.deck_cards_data   = []
        self.avail_scroll      = 0
        self.deck_scroll       = 0
        self.search_text       = ""
        self.search_active     = False
        self.deck_search_text  = ""
        self.deck_search_active = False
        self.type_filter       = "ALL"
        self.deck_type_filter  = "ALL"
        
        # Sub-filters state
        self.attr_filter       = "ALL"
        self.subtype_filter    = "ALL"
        self.deck_attr_filter  = "ALL"
        self.deck_subtype_filter = "ALL"
        
        self.hover_sprite      = None
        self.hover_in_deck     = False
        self.detail_card       = None
        self.drag_sprite       = None
        self._tex_cache        = OrderedDict()  # LRU: move_to_end on hit, popitem(last=False) on evict
        self._THUMB_LIMIT      = None  # set from DB in setup()
        self._DETAIL_LIMIT     = 20
        self._free_on_exit     = False  # set from DB in setup()
        self.mx = self.my      = 0
        self.lang              = "en"
        self.available_langs   = ["en", "es"] # Fallback, will be updated in setup()

        # New deck dialog state
        self.show_dialog = False
        self.dialog_input = ""
        self.dialog_panel = None
        self.btn_ok = None
        self.btn_cancel = None

    def on_show_view(self):
        ctx = self.window.ctx
        self.dialog_panel = ShaderPanel(ctx, SW // 2, SH // 2, 400, 200, title="Nuevo Mazo")
        self.btn_ok = ShaderButton(ctx, SW // 2 - 80, SH // 2 - 40, 120, 40, "Crear")
        self.btn_cancel = ShaderButton(ctx, SW // 2 + 80, SH // 2 - 40, 120, 40, "Cancelar")
        
        # New copy button for details panel
        self.btn_copy = ShaderButton(ctx, P3_X2 - 60, P3_Y2 - 30, 80, 28, "Copiar")
        self.btn_copy.radius = 5
        self.btn_copy.font_size = 10

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

        self.all_cards = self.db.get_cards(lang=self.lang)
        self.available_langs = self.db.get_available_languages()
        
        # If Spanish is available, start with it (as requested in Spanish context)
        if "es" in self.available_langs:
            self.lang = "es"
            self.all_cards = self.db.get_cards(lang=self.lang)

        decks = self.db.get_all_decks()
        if self.current_deck_id is None and decks:
            self.current_deck_id   = decks[0]['id']
            self.current_deck_name = decks[0]['name']
        elif self.current_deck_id:
            # Refresh name from DB
            deck_info = next((d for d in decks if d['id'] == self.current_deck_id), None)
            if deck_info:
                self.current_deck_name = deck_info['name']
            else:
                # Fallback to first if not found
                if decks:
                    self.current_deck_id = decks[0]['id']
                    self.current_deck_name = decks[0]['name']

        # UI elements MUST be init before display updates (which trigger recalc_hover)
        self._init_ui_elements()

        self.load_deck()
        self.update_avail_display()
        self.update_deck_display()
        
    def _init_ui_elements(self):
        ctx = self.window.ctx
        # Toolbar
        self.tb_objs = []
        for cx, lbl in self._toolbar_btns():
            # "Regresar" es más largo, le damos más espacio
            w = 175 if "Regresar" in lbl else 150
            btn = ShaderButton(ctx, cx, SH - TOP_BAR_H // 2, w, 36, lbl)
            self.tb_objs.append(btn)
        
        # Deck selection dialog state
        self.show_deck_list = False
        self.available_decks = []
            
        # Panel 1 Filters
        h1_y = P1_Y2 - 30
        sbw = 240
        sx = P1_X1 + (P1_X2 - P1_X1) // 2 - sbw // 2
        fx = sx + sbw + 20
        bw, bh = 100, 30
        self.p1_f_objs = {}
        for code, lbl, col in [("MONSTER", "Monstruos", C_MONSTER), ("SPELL", "Magias", C_SPELL), ("TRAP", "Trampas", C_TRAP)]:
            btn = ShaderButton(ctx, fx + bw // 2, h1_y, bw, bh, lbl)
            btn.active_color = col
            self.p1_f_objs[code] = btn
            fx += bw + 8
            
        # Panel 1 Sub-filters
        smy = h1_y - 35
        smw, smh = 62, 22
        gap = 5
        smx_start = sx + sbw // 2 - (13 * (smw + gap) + 15) // 2
        self.p1_sub_objs = {}
        # Attributes
        smx = smx_start
        for attr, col in [("DARK", (160, 80, 200)), ("LIGHT", (240, 230, 80)), ("EARTH", (140, 110, 60)), 
                          ("WATER", (60, 160, 230)), ("FIRE", (240, 100, 40)), ("WIND", (80, 200, 120))]:
            btn = ShaderButton(ctx, smx + smw // 2, smy, smw, smh, attr)
            btn.active_color = col
            btn.radius = 6
            btn.font_size = 10
            self.p1_sub_objs[attr] = btn
            smx += smw + gap
        # Subtypes
        smx += 20
        for stype in ["Normal", "Effect", "Ritual", "Fusion", "Synchro", "Xyz", "Link"]:
            btn = ShaderButton(ctx, smx + smw // 2, smy, smw, smh, stype)
            btn.active_color = BLUE
            btn.radius = 6
            btn.font_size = 10
            self.p1_sub_objs[stype] = btn
            smx += smw + gap

        # Panel 2 Filters
        h2_y = P2_Y2 - 25
        tsx = P2_X1 + (P2_X2 - P2_X1) // 2 - sbw // 2
        dfx_start = tsx + sbw + 20
        self.p2_f_objs = {}
        curr_fx = dfx_start
        for code, lbl, col in [("MONSTER", "Monstruos", C_MONSTER), ("SPELL", "Magias", C_SPELL), ("TRAP", "Trampas", C_TRAP)]:
            w = 175 if code == "MONSTER" else 135
            btn = ShaderButton(ctx, curr_fx + w // 2, h2_y, w, bh, lbl)
            btn.active_color = col
            self.p2_f_objs[code] = btn
            curr_fx += w + 8
            
        # Panel 2 Sub-filters
        smy = h2_y - 35
        self.p2_sub_objs = {}
        smx = tsx + sbw // 2 - (13 * (smw + gap) + 15) // 2
        for attr, col in [("DARK", (160, 80, 200)), ("LIGHT", (240, 230, 80)), ("EARTH", (140, 110, 60)), 
                          ("WATER", (60, 160, 230)), ("FIRE", (240, 100, 40)), ("WIND", (80, 200, 120))]:
            btn = ShaderButton(ctx, smx + smw // 2, smy, smw, smh, attr)
            btn.active_color = col
            btn.radius = 6
            btn.font_size = 10
            self.p2_sub_objs[attr] = btn
            smx += smw + gap
        smx += 20
        for stype in ["Normal", "Effect", "Ritual", "Fusion", "Synchro", "Xyz", "Link"]:
            btn = ShaderButton(ctx, smx + smw // 2, smy, smw, smh, stype)
            btn.active_color = BLUE
            btn.radius = 6
            btn.font_size = 10
            self.p2_sub_objs[stype] = btn
            smx += smw + gap

        # Language button
        self.btn_lang = ShaderButton(ctx, SW - PAD - 715, SH - TOP_BAR_H // 2, 80, 36, f"Lang: {self.lang.upper()}")
        self.tb_objs.append(self.btn_lang)

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_deck(self):
        self.deck_cards_data = (
            self.db.get_deck_cards(self.current_deck_id, lang=self.lang)
            if self.current_deck_id else []
        )

    def get_filtered(self):
        q = self.search_text.lower()
        result = []
        for c in self.all_cards:
            if q and q not in c.get('name', '').lower():
                continue
            
            ct = c.get('card_type', '')
            
            # Global Type Filter
            if self.type_filter != 'ALL':
                if self.type_filter == 'NO_IMG':
                    path = f"images/{c.get('image_name', '')}"
                    if os.path.exists(path): continue
                elif ct != self.type_filter:
                    continue
            
            # Monster Sub-filters
            if self.type_filter == 'MONSTER':
                if self.attr_filter != "ALL" and c.get('attribute') != self.attr_filter:
                    continue
                if self.subtype_filter != "ALL":
                    # Check if subtype_filter is in the card's 'type' string (e.g. 'Effect' in 'Spellcaster/Effect')
                    card_subtypes = (c.get('type') or '').lower()
                    if self.subtype_filter.lower() not in card_subtypes:
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
        
        HEADER_H = 100
        usable_w = (P1_X2 - P1_X1) - PAD * 2
        usable_h = (P1_Y2 - P1_Y1) - HEADER_H - PAD
        
        CARD_STEP_X = CW + 12
        CARD_STEP_Y = CH + 15
        
        max_cols = int(usable_w // CARD_STEP_X)
        max_rows = int(usable_h // CARD_STEP_Y)
        
        cards_per_page = max_cols * max_rows
        
        filtered = self.get_filtered()
        visible_cards = filtered[self.avail_scroll * max_cols:]
        visible_cards = visible_cards[:cards_per_page]

        for idx, card in enumerate(visible_cards):
            col = idx % max_cols
            row = idx // max_cols
            cx = P1_X1 + PAD + col * CARD_STEP_X + CW // 2
            cy = P1_Y2 - HEADER_H - row * CARD_STEP_Y - CH // 2
            
            tex = self._get_thumb(card.get('image_name'))
            s  = CardSprite(card, cx, cy, texture=tex)
            self.avail_sprites.append(s)

        self._recalc_hover()

    def update_deck_display(self):
        self.deck_sprites.clear()
        DECK_CARD_SCALE = 1.45  # Aumentado significativamente
        DCW = CW * DECK_CARD_SCALE
        DCH = CH * DECK_CARD_SCALE
        CARD_STEP_X = DCW + 5
        CARD_STEP_Y = DCH + 10
        
        usable_w = P2_X2 - P2_X1 - STATS_W - PAD
        max_cols = int(usable_w // CARD_STEP_X)
        max_rows = 1  # Ahora una sola fila
        cards_per_page = max_cols * max_rows
        
        # Filtrado de búsqueda en el mazo
        filtered_deck = self.deck_cards_data
        
        # Búsqueda por texto
        if getattr(self, 'deck_search_text', ''):
            q = self.deck_search_text.lower()
            filtered_deck = [c for c in filtered_deck if q in c.get('name', '').lower()]
            
        # Filtro por tipo global
        if getattr(self, 'deck_type_filter', 'ALL') != 'ALL':
            tf = self.deck_type_filter
            filtered_deck = [c for c in filtered_deck if c.get('card_type') == tf]
            
        # Filtros específicos de Monstruos para el Mazo
        if getattr(self, 'deck_type_filter', 'ALL') == 'MONSTER':
            if getattr(self, 'deck_attr_filter', 'ALL') != 'ALL':
                af = self.deck_attr_filter
                filtered_deck = [c for c in filtered_deck if c.get('attribute') == af]
            if getattr(self, 'deck_subtype_filter', 'ALL') != 'ALL':
                sf = self.deck_subtype_filter.lower()
                filtered_deck = [c for c in filtered_deck if sf in (c.get('type') or '').lower()]
            
        visible_cards = filtered_deck[self.deck_scroll : self.deck_scroll + cards_per_page]
        
        grid_cols = min(max_cols, (len(filtered_deck) + max_rows - 1) // max_rows)
        if grid_cols == 0:
            grid_cols = 1
            
        grid_w = grid_cols * CARD_STEP_X - 5
        start_x = P2_X1 + PAD + DCW / 2
        
        p2_inner_h = (P2_Y2 - 80) - P2_Y1
        mid_y = P2_Y1 + p2_inner_h / 2
        row_y = [mid_y] # Solo una fila central

        for idx, card in enumerate(visible_cards):
            col = idx
            row = 0
            
            cx = start_x + col * CARD_STEP_X
            cy = row_y[row]
            
            tex = self._get_thumb(card.get('image_name'))
            s  = CardSprite(card, cx, cy, texture=tex)
            s._qty = card.get('quantity', 1)
            
            s._card_scale *= DECK_CARD_SCALE
            s.scale = s._card_scale
            s._base_y = cy
            
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

        # Fondo global oscuro
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG)

        # Panel 1: Avail Cards
        _rrect_filled(P1_X1, P1_Y1, P1_X2, P1_Y2, 10, PANEL_BG)
        _rrect_outline(P1_X1, P1_Y1, P1_X2, P1_Y2, 10, PANEL_OUTLINE, 1)

        # Panel 2: Deck
        _rrect_filled(P2_X1, P2_Y1, P2_X2, P2_Y2, 10, PANEL_BG)
        _rrect_outline(P2_X1, P2_Y1, P2_X2, P2_Y2, 10, PANEL_OUTLINE, 1)

        # Panel 3: Details
        _rrect_filled(P3_X1, P3_Y1, P3_X2, P3_Y2, 10, PANEL_BG)
        _rrect_outline(P3_X1, P3_Y1, P3_X2, P3_Y2, 10, PANEL_OUTLINE, 1)

        # Toolbar
        for btn in self.tb_objs: btn.draw()

        # --- Interaction for Panel 1 (Available Cards) ---
        h1_y = P1_Y2 - 30
        sbw = 240
        sx = P1_X1 + (P1_X2 - P1_X1) // 2 - sbw // 2
        
        # Search box Panel 1
        hov_sb = _in_rect(self.mx, self.my, sx, h1_y - 16, sx + sbw, h1_y + 16)
        bg_sb = (*SEP, 150) if hov_sb or self.search_active else (*BTN, 150)
        _rrect_filled(sx, h1_y - 16, sx + sbw, h1_y + 16, 10, bg_sb)
        _rrect_outline(sx, h1_y - 16, sx + sbw, h1_y + 16, 10, (*BLUE, 200) if self.search_active else SEP, 1)
        
        txt = self.search_text + ("|" if self.search_active else "")
        if not txt and not self.search_active:
            arcade.draw_text("Buscar carta...", sx + 15, h1_y, (*TEXT, 100), font_size=11, anchor_y="center")
        else:
            arcade.draw_text(txt, sx + 15, h1_y, TEXT, font_size=11, anchor_y="center")
        arcade.draw_text("⌕", sx + sbw - 20, h1_y, (*TEXT, 150), font_size=14, anchor_y="center")

        # Filtros Panel 1
        for code, btn in self.p1_f_objs.items():
            btn.active = self.type_filter == code
            btn.draw()
            
        # ── Monster Sub-filters (Panel 1) ──
        if self.type_filter == 'MONSTER':
            for key, btn in self.p1_sub_objs.items():
                if key in ["DARK", "LIGHT", "EARTH", "WATER", "FIRE", "WIND"]:
                    btn.active = self.attr_filter == key
                else:
                    btn.active = self.subtype_filter == key
                btn.draw()
            
        arcade.draw_line(P1_X1, P1_Y2 - 90, P1_X2, P1_Y2 - 90, (*PANEL_OUTLINE, 200), 1)

        # ── Scroll hint P1 ──
        filtered   = self.get_filtered()
        cards_per_page = int((P1_X2 - P1_X1 - PAD * 2) // (CW + 12)) * int((P1_Y2 - P1_Y1 - 60 - PAD) // (CH + 15))
        total_pages = max(1, (len(filtered) + max(1, cards_per_page) - 1) // max(1, cards_per_page))
        curr_page = (self.avail_scroll * 1) + 1 # rough translation
        arcade.draw_text(
            f"Pág. {curr_page}/{total_pages}",
            P1_X2 - PAD, P1_Y1 + PAD, DIM, font_size=9, anchor_x="right"
        )

        # ── Available cards ──
        self.avail_sprites.draw()
        for s in self.avail_sprites:
            s.draw_glow(BLUE, "+")

        # ── Detail panel ──
        self._draw_detail()

        # ── Panel 2 Header ──
        h2_y = P2_Y2 - 25
        arcade.draw_text("Current Deck:", P2_X1 + PAD, h2_y, TEXT, font_size=16, bold=True, anchor_y="center")
        
        display_name = getattr(self, 'new_deck_name', '') + "_" if getattr(self, 'renaming_deck', False) else self.current_deck_name
        arcade.draw_text(f"{display_name} ({len(self.deck_cards_data)} cards)", P2_X1 + PAD + 150, h2_y, DIM if not getattr(self, 'renaming_deck', False) else GOLD, font_size=14, anchor_y="center")
        
        # Barra de búsqueda en el Panel 2 (Mazo) - Centrada
        sbw, sbh = 240, 32
        tsx = P2_X1 + (P2_X2 - P2_X1) // 2 - sbw // 2
        hov_sb = _in_rect(self.mx, self.my, tsx, h2_y - sbh//2, tsx + sbw, h2_y + sbh//2)
        bg_sb = (*SEP, 150) if hov_sb or self.deck_search_active else (*BTN, 150)
        _rrect_filled(tsx, h2_y - sbh//2, tsx + sbw, h2_y + sbh//2, 10, bg_sb)
        _rrect_outline(tsx, h2_y - sbh//2, tsx + sbw, h2_y + sbh//2, 10, (*BLUE, 200) if self.deck_search_active else SEP, 1)
        
        txt = self.deck_search_text + ("|" if self.deck_search_active else "")
        if not txt and not self.deck_search_active:
            arcade.draw_text("Buscar en mazo...", tsx + 15, h2_y, (*TEXT, 100), font_size=11, anchor_y="center")
        else:
            arcade.draw_text(txt, tsx + 15, h2_y, TEXT, font_size=11, anchor_y="center")
        arcade.draw_text("⌕", tsx + sbw - 20, h2_y, (*TEXT, 150), font_size=14, anchor_y="center")

        # ── Filtros del Mazo (Botones a la derecha del buscador) ──
        stats = self.get_deck_stats()
        for code, btn in self.p2_f_objs.items():
            btn.active = self.deck_type_filter == code
            # Actualizar label con count
            lbl = "Monstruos" if code == "MONSTER" else ("Magias" if code == "SPELL" else "Trampas")
            btn.label = f"[{stats[code.lower() + 's']}] {lbl}"
            btn.draw()

        # Total Badge (Al final de los botones del panel 2)
        # Sumamos los anchos variables: Monstruo(175) + Magia(135) + Trampa(135) + 3*Gap(8)
        dfx = tsx + sbw + 20 + (175 + 135 + 135 + 3 * 8)
        arcade.draw_text(f"Total: {stats['total']}/60", dfx + 10, h2_y, TEXT, font_size=11, bold=True, anchor_y="center")

        # ── Monster Sub-filters (Panel 2 / Deck) ──
        if self.deck_type_filter == 'MONSTER':
            for key, btn in self.p2_sub_objs.items():
                if key in ["DARK", "LIGHT", "EARTH", "WATER", "FIRE", "WIND"]:
                    btn.active = self.deck_attr_filter == key
                else:
                    btn.active = self.deck_subtype_filter == key
                btn.draw()

        arcade.draw_line(P2_X1, P2_Y2 - 80, P2_X2, P2_Y2 - 80, (*PANEL_OUTLINE, 200), 1)

        # ── Diálogos ──
        if self.show_dialog:
            self.dialog_panel.draw()
            # ... draw label and input ...
            arcade.draw_text("Nombre del Mazo:", SW // 2, SH // 2 + 30, TEXT, anchor_x="center")
            _rrect_filled(SW // 2 - 150, SH // 2 - 10, SW // 2 + 150, SH // 2 + 20, 5, BTN)
            arcade.draw_text(self.dialog_input + "|", SW // 2 - 140, SH // 2 + 5, TEXT, anchor_y="center")
            self.btn_ok.draw()
            self.btn_cancel.draw()
        
        if getattr(self, 'show_deck_list', False):
            # Panel de selección de deck
            ctx = self.window.ctx
            w, h = 400, 500
            px, py = SW // 2, SH // 2
            _rrect_filled(px - w//2, py - h//2, px + w//2, py + h//2, 12, (30, 30, 35, 240))
            _rrect_outline(px - w//2, py - h//2, px + w//2, py + h//2, 12, BLUE, 2)
            
            arcade.draw_text("Seleccionar Mazo", px, py + h//2 - 30, GOLD, font_size=16, bold=True, anchor_x="center")
            
            start_y = py + h//2 - 80
            for idx, d in enumerate(self.available_decks):
                dy = start_y - idx * 45
                color = BTN_ACT if d['id'] == self.current_deck_id else BTN
                hover = _in_rect(self.mx, self.my, px - 180, dy - 18, px + 180, dy + 18)
                if hover: color = BTN_HOV
                
                _rrect_filled(px - 180, dy - 18, px + 180, dy + 18, 5, color)
                arcade.draw_text(f"{d['name']} ({d['card_count']})", px - 170, dy, TEXT, anchor_y="center")
            
            arcade.draw_text("[ESC] para Cerrar", px, py - h//2 + 20, DIM, font_size=10, anchor_x="center")

        self.deck_sprites.draw()
        for s in self.deck_sprites:
            s.draw_qty_badge(s._qty)
            
        # ── Footer Text ──
        arcade.draw_text("🖱 Left Click: Add to deck | Right Click: Remove | Mouse Wheel: Scroll",
                         SW // 2, BOTTOM_BAR_H // 2, DIM, font_size=11, anchor_x="center", anchor_y="center")


        # ── Ghost para arrastrar (Drag & Drop) ──
        if getattr(self, 'drag_sprite', None):
            s = arcade.Sprite()
            s.texture = self.drag_sprite.texture
            s.scale = self.drag_sprite._card_scale * 1.18
            s.center_x = getattr(self, 'drag_ghost_x', self.mx)
            s.center_y = getattr(self, 'drag_ghost_y', self.my)
            s.alpha = 200
            sl = arcade.SpriteList()
            sl.append(s)
            sl.draw()

    def _draw_detail(self):
        dpx = P3_X1 + (P3_X2 - P3_X1) // 2

        # Header "Card Details"
        arcade.draw_text("Card Details", P3_X1 + PAD, P3_Y2 - 30, TEXT, font_size=16, bold=True, anchor_y="center")
        self.btn_copy.draw()
        arcade.draw_line(P3_X1, P3_Y2 - 60, P3_X2, P3_Y2 - 60, (*PANEL_OUTLINE, 200), 1)

        if not self.detail_card:
            return

        card    = self.detail_card
        tex     = self._tex_cache.get(card.get('image_name'))
        if not tex:
            tex = self._get_thumb(card.get('image_name'))
            
        img_h   = 240
        img_y   = P3_Y2 - 60 - img_h // 2 - 10

        if tex:
            scale = min((DETAIL_W - 40) / tex.width, img_h / tex.height)
            s = arcade.Sprite()
            s.texture  = tex
            s.scale    = scale
            s.center_x = dpx
            s.center_y = img_y
            
            # Yellow Glow like reference
            _rrect_outline(dpx - (tex.width*scale)/2 - 4, img_y - (tex.height*scale)/2 - 4,
                           dpx + (tex.width*scale)/2 + 4, img_y + (tex.height*scale)/2 + 4, 
                           10, (*GOLD, 100), 6)
            _rrect_outline(dpx - (tex.width*scale)/2 - 2, img_y - (tex.height*scale)/2 - 2,
                           dpx + (tex.width*scale)/2 + 2, img_y + (tex.height*scale)/2 + 2, 
                           10, (*GOLD, 200), 2)
            
            sl = arcade.SpriteList()
            sl.append(s)
            sl.draw()
        else:
            arcade.draw_lrbt_rectangle_filled(
                P3_X1 + 20, P3_X2 - 20,
                img_y - img_h // 2, img_y + img_h // 2,
                (55, 55, 72)
            )

        # Name
        ny  = img_y - img_h // 2 - 25
        title = card.get('name', '?')
        arcade.draw_text(title, P3_X1 + PAD, ny, TEXT, font_size=16, bold=True, anchor_y="center")

        # Horizontal Attributes
        attr  = card.get('attribute', 'N/A')
        lvl   = card.get('level', '?')
        tipo  = (card.get('type') or 'N/A').split()[0]
        
        attr_col = {'DARK': (160, 80, 200), 'LIGHT': (240, 230, 80),
                    'FIRE': (240, 100, 40), 'WATER': (60, 160, 230),
                    'EARTH': (140, 110, 60), 'WIND': (80, 200, 120),
                    'DIVINE': (240, 200, 80)}.get(attr, GOLD)

        sy = ny - 30
        ax = P3_X1 + PAD
        
        arcade.draw_circle_filled(ax + 8, sy, 8, attr_col)
        arcade.draw_text(attr[0] if attr else "?", ax + 8, sy, BG, font_size=9, bold=True, anchor_x="center", anchor_y="center")
        arcade.draw_text("Attr.", ax + 22, sy, DIM, font_size=10, anchor_y="center")
        
        ax += 90
        arcade.draw_circle_filled(ax + 8, sy, 8, (250, 100, 0))
        arcade.draw_text("★", ax + 8, sy, BG, font_size=9, bold=True, anchor_x="center", anchor_y="center")
        arcade.draw_text("Nivel", ax + 22, sy, DIM, font_size=10, anchor_y="center")
        
        ax += 90
        arcade.draw_circle_filled(ax + 8, sy, 8, (150, 50, 200))
        arcade.draw_text("◉", ax + 8, sy, BG, font_size=9, bold=True, anchor_x="center", anchor_y="center")
        arcade.draw_text("Tipo", ax + 22, sy, DIM, font_size=10, anchor_y="center")

        # Effect text
        effect = card.get('text', '')
        if effect:
            arcade.draw_text(
                effect, P3_X1 + PAD, sy - 30,
                (175, 175, 175), font_size=10,
                width=DETAIL_W - PAD * 2, multiline=True, anchor_y="top"
            )

    # ── Events ────────────────────────────────────────────────────────────────

    def _toolbar_btns(self):
        return [
            (SW - PAD - 75,  "Guardar Mazo"),
            (SW - PAD - 245, "Nuevo Mazo"),
            (SW - PAD - 415, "Mis Decks"),
            (SW - PAD - 585, "Regresar al Juego")
        ]

    def _open_deck_list(self):
        self.available_decks = self.db.get_all_decks_with_card_count()
        self.show_deck_list = True

    def on_update(self, delta_time):
        if getattr(self, 'show_dialog', False) or getattr(self, 'show_deck_list', False):
            return

        for s in self.avail_sprites:
            is_hovered = (s is self.hover_sprite and not self.hover_in_deck)
            s.update_animation(delta_time, is_hovered)
            
        for s in self.deck_sprites:
            is_hovered = (s is self.hover_sprite and self.hover_in_deck)
            s.update_animation(delta_time, is_hovered)

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y
        
        # UI Buttons hover
        for btn in self.tb_objs: btn.on_mouse_motion(x, y)
        for btn in self.p1_f_objs.values(): btn.on_mouse_motion(x, y)
        if self.type_filter == 'MONSTER':
            for btn in self.p1_sub_objs.values(): btn.on_mouse_motion(x, y)
        for btn in self.p2_f_objs.values(): btn.on_mouse_motion(x, y)
        if self.deck_type_filter == 'MONSTER':
            for btn in self.p2_sub_objs.values(): btn.on_mouse_motion(x, y)
        
        if getattr(self, 'btn_copy', None):
            self.btn_copy.on_mouse_motion(x, y)
            
        if getattr(self, 'show_dialog', False) or getattr(self, 'show_deck_list', False):
            if getattr(self, 'btn_ok', None):
                self.btn_ok.on_mouse_motion(x, y)
                self.btn_cancel.on_mouse_motion(x, y)
            return

        if getattr(self, 'drag_sprite', None):
            self.drag_ghost_x = x
            self.drag_ghost_y = y
            return  # Pausamos el highlight del hover durante el arrastre

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
        if getattr(self, 'show_deck_list', False):
            w, h = 400, 500
            px, py = SW // 2, SH // 2
            start_y = py + h//2 - 80
            for idx, d in enumerate(self.available_decks):
                dy = start_y - idx * 45
                if _in_rect(x, y, px - 180, dy - 18, px + 180, dy + 18):
                    self.current_deck_id = d['id']
                    self.current_deck_name = d['name']
                    self.load_deck()
                    self.update_deck_display()
                    self.show_deck_list = False
                    return
            if not _in_rect(x, y, px - w//2, py - h//2, px + w//2, py + h//2):
                self.show_deck_list = False
            return

        if self.show_dialog:
            if button == arcade.MOUSE_BUTTON_LEFT:
                if getattr(self, 'btn_ok', None) and self.btn_ok.contains(x, y):
                    self._confirm_new_deck()
                elif getattr(self, 'btn_cancel', None) and self.btn_cancel.contains(x, y):
                    self.show_dialog = False
            return

        # Check renaming click
        h2_y = P2_Y2 - 25
        if _in_rect(x, y, P2_X1 + 140, h2_y - 15, P2_X1 + 350, h2_y + 15):
            self.renaming_deck = not getattr(self, 'renaming_deck', False)
            if self.renaming_deck:
                self.new_deck_name = self.current_deck_name
            else:
                if hasattr(self, 'new_deck_name') and self.new_deck_name.strip():
                    self.db.rename_deck(self.current_deck_id, self.new_deck_name.strip())
                    self.current_deck_name = self.new_deck_name.strip()
            return
        elif getattr(self, 'renaming_deck', False):
            # Clicked outside while renaming, save and exit
            self.renaming_deck = False
            if hasattr(self, 'new_deck_name') and self.new_deck_name.strip():
                self.db.rename_deck(self.current_deck_id, self.new_deck_name.strip())
                self.current_deck_name = self.new_deck_name.strip()
    
        # Toolbar
        for btn in self.tb_objs:
            if btn.contains(x, y):
                lbl = btn.label
                if "Regresar" in lbl: self._go_back()
                elif "Guardar" in lbl: self._save_deck()
                elif "Nuevo"  in lbl: self._new_deck()
                elif "Mis Decks" in lbl: self._open_deck_list()
                elif "Lang:" in lbl: self._change_lang()
                return

        if getattr(self, 'btn_copy', None) and self.btn_copy.contains(x, y):
            self._copy_card_info()
            return

        # --- Interaction for Panel 1 (Available Cards) ---
        h1_y = P1_Y2 - 30
        sbw = 240
        sx = P1_X1 + (P1_X2 - P1_X1) // 2 - sbw // 2
        
        # Search box focus Panel 1
        if _in_rect(x, y, sx, h1_y - 16, sx + sbw, h1_y + 16):
            self.search_active = True
            self.deck_search_active = False
            return
            
        # Filter clicks Panel 1
        for code, btn in self.p1_f_objs.items():
            if btn.contains(x, y):
                self.type_filter = "ALL" if self.type_filter == code else code
                self.avail_scroll = 0
                self.update_avail_display()
                return

        # --- Interaction for Panel 2 (Current Deck) ---
        h2_y = P2_Y2 - 25
        tsx = P2_X1 + (P2_X2 - P2_X1) // 2 - sbw // 2
        
        # Search box focus Panel 2
        if _in_rect(x, y, tsx, h2_y - 16, tsx + sbw, h2_y + 16):
            self.deck_search_active = True
            self.search_active = False
            return
            
        # Filter clicks Panel 2
        for code, btn in self.p2_f_objs.items():
            if btn.contains(x, y):
                self.deck_type_filter = "ALL" if self.deck_type_filter == code else code
                self.deck_scroll = 0
                self.update_deck_display()
                return

        self.search_active = False
        self.deck_search_active = False

        # --- Sub-filter clicks Panel 1 ---
        if self.type_filter == 'MONSTER':
            for key, btn in self.p1_sub_objs.items():
                if btn.contains(x, y):
                    if key in ["DARK", "LIGHT", "EARTH", "WATER", "FIRE", "WIND"]:
                        self.attr_filter = "ALL" if self.attr_filter == key else key
                    else:
                        self.subtype_filter = "ALL" if self.subtype_filter == key else key
                    self.avail_scroll = 0
                    self.update_avail_display()
                    return

        # --- Sub-filter clicks Panel 2 ---
        if self.deck_type_filter == 'MONSTER':
            for key, btn in self.p2_sub_objs.items():
                if btn.contains(x, y):
                    if key in ["DARK", "LIGHT", "EARTH", "WATER", "FIRE", "WIND"]:
                        self.deck_attr_filter = "ALL" if self.deck_attr_filter == key else key
                    else:
                        self.deck_subtype_filter = "ALL" if self.deck_subtype_filter == key else key
                    self.deck_scroll = 0
                    self.update_deck_display()
                    return

        # Iniciar drag & drop para cartas
        av = arcade.get_sprites_at_point((x, y), self.avail_sprites)
        dk = arcade.get_sprites_at_point((x, y), self.deck_sprites)
        
        if av and button == arcade.MOUSE_BUTTON_LEFT and self.current_deck_id:
            self.drag_sprite = av[-1]
            self.drag_source = 'avail'
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_ghost_x = x
            self.drag_ghost_y = y
            return

        if dk and button == arcade.MOUSE_BUTTON_LEFT and self.current_deck_id:
            self.drag_sprite = dk[-1]
            self.drag_source = 'deck'
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_ghost_x = x
            self.drag_ghost_y = y
            return

    def on_mouse_release(self, x, y, button, modifiers):
        if getattr(self, 'drag_sprite', None) and button == arcade.MOUSE_BUTTON_LEFT:
            dx = x - self.drag_start_x
            dy = y - self.drag_start_y
            dist = (dx**2 + dy**2)**0.5
            
            in_deck_area = _in_rect(x, y, P2_X1, P2_Y1, P2_X2, P2_Y2)
            cid = self.drag_sprite.card_data['cid']
            
            if dist < 10:  # Fue un clic
                if self.drag_source == 'avail':
                    if self.db.add_card_to_deck(self.current_deck_id, cid):
                        self.load_deck()
                        self.update_deck_display()
                elif self.drag_source == 'deck':
                    self.db.remove_card_from_deck(self.current_deck_id, cid)
                    self.load_deck()
                    self.update_deck_display()
            else:  # Fue un arrastre (Drag & Drop)
                if self.drag_source == 'avail' and in_deck_area:
                    if self.db.add_card_to_deck(self.current_deck_id, cid):
                        self.load_deck()
                        self.update_deck_display()
                elif self.drag_source == 'deck' and not in_deck_area:
                    self.db.remove_card_from_deck(self.current_deck_id, cid)
                    self.load_deck()
                    self.update_deck_display()
                    
            self.drag_sprite = None
            self._recalc_hover()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if _in_rect(x, y, P1_X1, P1_Y1, P1_X2, P1_Y2):
            HEADER_H = 100
            CARD_STEP_X = CW + 12
            CARD_STEP_Y = CH + 15
            usable_w = (P1_X2 - P1_X1) - PAD * 2
            usable_h = (P1_Y2 - P1_Y1) - HEADER_H - PAD
            max_cols = int(usable_w // CARD_STEP_X)
            max_rows = int(usable_h // CARD_STEP_Y)
            cards_per_page = max_cols * max_rows
            max_scroll = max(0, (len(self.get_filtered()) + max(1, cards_per_page) - 1) // max(1, cards_per_page))
            
            delta = -1 if scroll_y > 0 else 1
            self.avail_scroll = max(0, min(max_scroll, self.avail_scroll + delta))
            self.update_avail_display()
        elif _in_rect(x, y, P2_X1, P2_Y1, P2_X2, P2_Y2):
            DECK_CARD_SCALE = 1.45
            DCW = CW * DECK_CARD_SCALE
            CARD_STEP_X = DCW + 5
            max_cols   = int(((P2_X2 - P2_X1) - PAD * 2 - STATS_W) // CARD_STEP_X)
            max_rows   = 1
            cards_per_page = max_cols * max_rows
            
            max_scroll = max(0, len(self.deck_cards_data) - cards_per_page)
            
            delta = -1 if (scroll_x > 0 or scroll_y < 0) else 1
            self.deck_scroll = max(0, min(max_scroll, self.deck_scroll + delta))
            self.update_deck_display()

    def on_text(self, text):
        if getattr(self, 'show_dialog', False):
            if text.isprintable():
                self.dialog_input += text
            return

        if getattr(self, 'renaming_deck', False):
            if text.isprintable():
                self.new_deck_name += text
            return
            
        if self.search_active:
            self.search_text += text
            self.avail_scroll = 0
            self.update_avail_display()
        elif self.deck_search_active:
            self.deck_search_text += text
            self.deck_scroll = 0
            self.update_deck_display()

    def on_key_press(self, symbol, modifiers):
        if getattr(self, 'show_dialog', False):
            if symbol == arcade.key.BACKSPACE:
                self.dialog_input = self.dialog_input[:-1]
            elif symbol == arcade.key.ENTER:
                self._confirm_new_deck()
            elif symbol == arcade.key.ESCAPE:
                self.show_dialog = False
            return

    def on_key_press(self, symbol, modifiers):
        if getattr(self, 'show_deck_list', False):
            if symbol == arcade.key.ESCAPE:
                self.show_deck_list = False
            return

        if self.show_dialog:
            if symbol == arcade.key.ENTER:
                self._confirm_new_deck()
            elif symbol == arcade.key.ESCAPE:
                self.show_dialog = False
            return
            
        if self.search_active:
            if symbol == arcade.key.BACKSPACE:
                self.search_text = self.search_text[:-1]
                self.avail_scroll = 0
                self.update_avail_display()
            elif symbol == arcade.key.ESCAPE:
                self.search_active = False

        elif self.deck_search_active:
            if symbol == arcade.key.BACKSPACE:
                self.deck_search_text = self.deck_search_text[:-1]
                self.deck_scroll = 0
                self.update_deck_display()
            elif symbol == arcade.key.ESCAPE:
                self.deck_search_active = False

        elif symbol == arcade.key.ESCAPE:
            self._go_back()
        
        elif symbol == arcade.key.C and (modifiers & arcade.key.MOD_CTRL):
            self._copy_card_info()

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
        self.show_dialog = True
        self.dialog_input = ""

    def _confirm_new_deck(self):
        name = self.dialog_input.strip()
        if not name:
            n = len(self.db.get_all_decks()) + 1
            name = f"Deck {n}"
        self.current_deck_id = self.db.create_deck(name)
        self.current_deck_name = name
        self.deck_scroll = 0
        self.load_deck()
        self.update_deck_display()
        self.show_dialog = False

    def _change_lang(self):
        # Cycle through available languages
        idx = self.available_langs.index(self.lang)
        self.lang = self.available_langs[(idx + 1) % len(self.available_langs)]
        
        # Update button label
        for btn in self.tb_objs:
            if "Lang:" in btn.label:
                btn.label = f"Lang: {self.lang.upper()}"
                break
        
        # Reload all data
        self.all_cards = self.db.get_cards(lang=self.lang)
        self.load_deck()
        self.update_avail_display()
        self.update_deck_display()
        
        # Invalidate detail card to force reload with new language if it's open
        if self.detail_card:
            cid = self.detail_card['cid']
            # Find the updated card data
            new_data = next((c for c in self.all_cards if c['cid'] == cid), None)
            if new_data:
                self.detail_card = new_data

    def _open_deck_list(self):
        self.available_decks = self.db.get_all_decks()
        self.show_deck_list = True

    def _copy_card_info(self):
        if not self.detail_card:
            return
        
        card = self.detail_card
        text = f"{card.get('name', '')}\n{card.get('attribute', '')} | {card.get('level', '')} | {card.get('type', '')}\n{card.get('text', '')}"
        
        try:
            # Intentar usar Gdk si está disponible
            from gi.repository import Gdk
            display = Gdk.Display.get_default()
            if display:
                clipboard = display.get_clipboard()
                clipboard.set(text)
        except Exception:
            # Fallback muy básico usando xclip en Linux o simplemente imprimiendo
            import subprocess
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
            except:
                print(f"[CLIPBOARD] Fallback print:\n{text}")

    def on_hide_view(self):
        if self._free_on_exit:
            self._release_atlas()
