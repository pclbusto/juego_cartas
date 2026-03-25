import os
import arcade
import constants
from card import Card
from zones import BoardManager
from database import DatabaseManager

SW = constants.SCREEN_WIDTH
SH = constants.SCREEN_HEIGHT
CW = constants.CARD_WIDTH
CH = constants.CARD_HEIGHT

LW = constants.LEFT_PANEL_W    # 260
RW = constants.RIGHT_PANEL_W   # 340
HH = constants.BOTTOM_HAND_H   # 140
TH = 36                         # top bar height

# Board bounds
BX1 = LW
BX2 = SW - RW
BY1 = HH
BY2 = SH - TH

# ── Colors — spec palette ─────────────────────────────────────────────────────
BG_DEEP  = (27,  30,  35)     # #1b1e23  main background
BOARD_BG = (22,  25,  30)     # slightly lighter for board
PANEL_BG = (44,  49,  58)     # #2c313a  panel containers
SEP      = (62,  68,  81)     # #3e4451  borders
TEXT     = (230, 232, 238)
DIM      = (110, 115, 128)
GOLD     = (255, 200,  50)    # active / selected states
BLUE_N   = (  0, 170, 255)    # #00aaff  player accent
RED_N    = (255,  76,  76)    # #ff4c4c  opponent accent
GREEN_N  = ( 50, 210,  90)
BTN      = ( 48,  53,  64)
BTN_HOV  = ( 62,  68,  80)
BTN_ACT  = ( 20,  90, 200)

C_MONSTER = (220, 130, 50)
C_SPELL   = (80,  180, 255)
C_TRAP    = (210,  90, 110)

_ATTR_COLORS = {
    'DARK':  (160, 80,  200),
    'LIGHT': (240, 230,  80),
    'FIRE':  (240, 100,  40),
    'WATER': ( 60, 160, 230),
    'EARTH': (140, 110,  60),
    'WIND':  ( 80, 200, 120),
    'DIVINE':(240, 200,  80),
}

_ZONE_STYLES = {
    "Mon":   ((50, 22,  6, 140), (220, 110,  50)),
    "S/T":   (( 6, 25, 60, 140), ( 55, 135, 230)),
    "Field": ((10, 48, 16, 140), ( 70, 185,  75)),
    "GY":    ((32, 32, 32, 140), (130, 130, 130)),
    "Deck":  ((20, 20, 48, 140), ( 90,  90, 175)),
    "Extra": ((20, 20, 48, 140), ( 90,  90, 175)),
    "EMZ":   ((35, 35, 48, 140), (150, 150, 200)),
}

def _zone_style(name):
    for k, v in _ZONE_STYLES.items():
        if k in name:
            return v
    return ((35, 35, 35, 140), (100, 100, 100))

def _zone_abbr(name):
    for k in ["Deck", "Extra", "Field", "GY", "EMZ"]:
        if k in name:
            return k
    if "Mon" in name:
        return "MON"
    if "S/T" in name:
        return "S/T"
    return name.split()[-1][:3].upper()

# ── Draw helpers ──────────────────────────────────────────────────────────────

def _in_rect(x, y, x1, y1, x2, y2):
    return x1 <= x <= x2 and y1 <= y <= y2

def _rrect_filled(x1, y1, x2, y2, r, color):
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    arcade.draw_lrbt_rectangle_filled(x1 + r, x2 - r, y1, y2, color)
    arcade.draw_lrbt_rectangle_filled(x1, x2, y1 + r, y2 - r, color)
    for cx, cy in [(x1+r, y1+r), (x2-r, y1+r), (x1+r, y2-r), (x2-r, y2-r)]:
        arcade.draw_circle_filled(cx, cy, r, color)

def _rrect_outline(x1, y1, x2, y2, r, color, lw=1):
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    arcade.draw_line(x1+r, y1,  x2-r, y1,  color, lw)
    arcade.draw_line(x1+r, y2,  x2-r, y2,  color, lw)
    arcade.draw_line(x1, y1+r,  x1, y2-r,  color, lw)
    arcade.draw_line(x2, y1+r,  x2, y2-r,  color, lw)
    d = r * 2
    arcade.draw_arc_outline(x1+r, y1+r, d, d, color, 180, 270, lw)
    arcade.draw_arc_outline(x2-r, y1+r, d, d, color, 270, 360, lw)
    arcade.draw_arc_outline(x2-r, y2-r, d, d, color,   0,  90, lw)
    arcade.draw_arc_outline(x1+r, y2-r, d, d, color,  90, 180, lw)

def _draw_btn(cx, cy, w, h, label, hovered=False, active=False, color=None):
    x1, x2 = cx - w//2, cx + w//2
    y1, y2 = cy - h//2, cy + h//2
    bg = (color or BTN_ACT) if active else (BTN_HOV if hovered else BTN)
    _rrect_filled(x1, y1, x2, y2, 6, bg)
    border = (*((color or BTN_ACT)), 180) if active else (*SEP, 100)
    _rrect_outline(x1, y1, x2, y2, 6, border, 1)
    arcade.draw_text(label, cx, cy, TEXT, font_size=10,
                     anchor_x="center", anchor_y="center")

def _neon_circle(cx, cy, r, color, label="", font=18):
    """Avatar circle with neon glow rings."""
    arcade.draw_circle_filled(cx, cy, r, (28, 30, 40))
    for dr, alpha in [(r+6, 25), (r+4, 55), (r+2, 100)]:
        arcade.draw_circle_outline(cx, cy, dr, (*color, alpha), 1)
    arcade.draw_circle_outline(cx, cy, r, (*color, 220), 2)
    if label:
        arcade.draw_text(label, cx, cy, (*color, 230), font_size=font,
                         bold=True, anchor_x="center", anchor_y="center")

def _neon_lp(cx, cy, lp, color):
    """Life points with neon glow text."""
    txt = f"{lp:,}"
    # glow
    arcade.draw_text(txt, cx, cy, (*color, 50), font_size=30, bold=True,
                     anchor_x="center", anchor_y="center")
    arcade.draw_text(txt, cx-1, cy+1, (*color, 90), font_size=29, bold=True,
                     anchor_x="center", anchor_y="center")
    # sharp
    arcade.draw_text(txt, cx, cy, color, font_size=27, bold=True,
                     anchor_x="center", anchor_y="center")
    arcade.draw_text("PV", cx + len(txt)*9 + 6, cy - 8, (*color, 170),
                     font_size=9, bold=True)

def _resource_row(x, y, color, hand, gy):
    """Hand + GY counts with small icons."""
    arcade.draw_text("♦", x, y, (*color, 210), font_size=12, anchor_y="center")
    arcade.draw_text(str(hand), x + 16, y, TEXT, font_size=12,
                     bold=True, anchor_y="center")
    arcade.draw_text("MANO", x + 32, y, DIM, font_size=8, anchor_y="center")

    gx = x + 90
    arcade.draw_text("✦", gx, y, (*color, 180), font_size=11, anchor_y="center")
    arcade.draw_text(str(gy), gx + 15, y, TEXT, font_size=12,
                     bold=True, anchor_y="center")
    arcade.draw_text("CEQ", gx + 31, y, DIM, font_size=8, anchor_y="center")


# ── View ──────────────────────────────────────────────────────────────────────

_PHASES = ["DP", "SP", "M1", "BP", "M2", "EP"]
_PHASE_LABELS = {
    "DP": "Robo",  "SP": "Reserva", "M1": "Principal 1",
    "BP": "Batalla", "M2": "Principal 2", "EP": "Fin",
}

class GameView(arcade.View):

    def __init__(self):
        super().__init__()
        self.db       = DatabaseManager()
        self.card_list = []           # plain list so Card.draw() is called per card
        self.held_card = None
        self.hover_card = None
        self.held_card_original_position = None
        self.deck_name = ""
        self.mx = self.my = 0

        # Deck selection overlay state
        self._selecting  = True       # True = show deck picker
        self._all_decks  = []         # list of deck dicts
        self._sel_scroll = 0          # scroll offset (future use)

        # Full-size texture cache for right panel detail view
        self._detail_cache: dict[str, object] = {}   # image_name -> arcade.Texture | None

        # Duel state (mock values until game logic is implemented)
        self.player_lp     = 8000
        self.opponent_lp   = 4000
        self.player_hand   = 5
        self.opponent_hand = 5
        self.player_gy     = 0
        self.opponent_gy   = 0
        self.current_phase = "M1"
        self.duel_log: list[tuple[str, tuple]] = [
            ("Duelo iniciado", DIM),
        ]

        bw = (SW - RW - LW)
        bh = (SH - TH) - HH
        board_cx = LW + bw / 2
        board_cy = HH + bh / 2
        step_x = min(bw / 8,  CW + 16)
        step_y = min(bh / 5.5, CH + 14)
        self.board_manager = BoardManager(board_cx, board_cy, step_x, step_y)
        self.selected_field_card = None   # card selected on the field

    def setup(self):
        self._all_decks = self.db.get_all_decks()
        self._selecting = True        # always start at deck picker

    def _load_deck(self, deck: dict):
        """Populate the hand from a saved deck dict."""
        self.card_list.clear()
        self.deck_name = deck['name']
        flat = []
        for cd in self.db.get_deck_cards(deck['id']):
            for _ in range(cd.get('quantity', 1)):
                flat.append(cd)

        bw  = BX2 - BX1
        n   = min(5, len(flat))
        gap = min(CW + 10, (bw - 40) / max(n, 1))
        cx0 = LW + bw / 2 - gap * (n - 1) / 2
        
        # Center cards vertically inside the upper portion of HH to avoid bottom OS clipping
        card_y = HH - CH/2 - 12
        for i, cd in enumerate(flat[:5]):
            c = Card(card_data=cd)
            c.position = (cx0 + gap * i, card_y)
            c._base_y = card_y
            self.card_list.append(c)

        self.player_hand = len(self.card_list)
        self._log(f"Deck cargado: {self.deck_name}", BLUE_N)
        self._log(f"Jugador robó {self.player_hand} cartas", BLUE_N)
        self._selecting = False

    # ── Update & Draw ─────────────────────────────────────────────────────────

    def on_update(self, dt):
        for card in self.card_list:
            card.update()

    def on_draw(self):
        self.clear()

        if self._selecting:
            self._draw_deck_selector()
            return

        # Global background
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG_DEEP)

        # Board area
        arcade.draw_lrbt_rectangle_filled(BX1, BX2, BY1, BY2, BOARD_BG)

        # Board glass container
        pad = 12
        _rrect_outline(BX1 + pad, BX2 - pad, BY1 + pad, BY2 - pad, 10, (*SEP, 180), 1)

        # Center Line
        mid_y = (BY1 + BY2) / 2
        arcade.draw_line(BX1 + pad, mid_y, BX2 - pad, mid_y, (*SEP, 120), 1)

        # Zones
        for zone in self.board_manager.zones:
            self._draw_zone(zone)

        # Field card selection glow (blue circle, like the mockup)
        if self.selected_field_card:
            fc = self.selected_field_card
            r = max(CW, CH) // 2 + 6
            for dr, al in [(r+12, 12), (r+8, 30), (r+4, 65), (r+1, 120)]:
                arcade.draw_circle_outline(fc.center_x, fc.center_y, dr,
                                           (*BLUE_N, al), 2)
            arcade.draw_circle_outline(fc.center_x, fc.center_y, r,
                                       (*BLUE_N, 240), 2)

        # Hand container (Floating Box)
        hw  = min(640, BX2 - BX1 - 20)
        hh  = CH + 16
        hx1 = BX1 + (BX2 - BX1) / 2 - hw / 2
        hx2 = hx1 + hw
        hy2 = HH - 4
        hy1 = hy2 - hh

        _rrect_filled(hx1, hy1, hx2, hy2, 10, (14, 17, 24, 235))
        _rrect_outline(hx1, hy1, hx2, hy2, 10, (*SEP, 140), 1)

        # "Mano" label inside the hand box
        arcade.draw_text("MANO", hx1 + 10, (hy1 + hy2) / 2, (*DIM, 140),
                         font_size=8, bold=True,
                         anchor_x="left", anchor_y="center", rotation=90)

        # Tooltip above hand
        arcade.draw_text(
            "Click Izq: Seleccionar  ·  Click Der: Acción  ·  Rueda: Zoom",
            BX1 + (BX2 - BX1) / 2, hy2 + 10, (*DIM, 140), font_size=9,
            anchor_x="center", anchor_y="bottom"
        )

        # Cards in hand — loop so Card.draw() override is called
        for card in self.card_list:
            card.draw()

        # Held card glow ring
        if self.held_card:
            hc, hy_ = self.held_card.center_x, self.held_card.center_y
            for exp, al in [(8, 30), (5, 70), (2, 140)]:
                _rrect_outline(hc - CW//2 - exp, hy_ - CH//2 - exp,
                               hc + CW//2 + exp, hy_ + CH//2 + exp,
                               6, (*GOLD, al), 1)
            _rrect_outline(hc - CW//2 - 2, hy_ - CH//2 - 2,
                           hc + CW//2 + 2, hy_ + CH//2 + 2,
                           6, (*GOLD, 220), 2)

        # Hover card glow ring (hand cards)
        if self.hover_card and not self.held_card:
            hc, hy_ = self.hover_card.center_x, self.hover_card.center_y
            for exp, al in [(6, 20), (3, 60)]:
                _rrect_outline(hc - CW//2 - exp, hy_ - CH//2 - exp,
                               hc + CW//2 + exp, hy_ + CH//2 + exp,
                               6, (*BLUE_N, al), 1)

        self._draw_left_panel()
        self._draw_right_panel()
        self._draw_top_bar()

    def _get_detail_tex(self, image_name: str):
        """Load and cache a full-size texture for the detail panel."""
        if image_name in self._detail_cache:
            return self._detail_cache[image_name]
        tex = None
        path = f"images/{image_name}"
        if os.path.exists(path):
            try:
                tex = arcade.load_texture(path)
            except Exception:
                pass
        self._detail_cache[image_name] = tex
        return tex

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _draw_top_bar(self):
        y1 = SH - TH
        # Background
        arcade.draw_lrbt_rectangle_filled(0, SW, y1, SH, (20, 23, 30))
        arcade.draw_line(0, y1, SW, y1, (*SEP, 200), 1)

        # Title (left-ish)
        arcade.draw_text("Tablero de Duelo  YGO",
                         LW + 16, SH - TH / 2, DIM,
                         font_size=11, bold=False,
                         anchor_y="center")

        # Filter toggle buttons (center-right)
        filters = [("Monstruos", C_MONSTER), ("Hechizos", C_SPELL), ("Trampa", C_TRAP)]
        bw, bh_ = 90, 22
        gap = 8
        total = len(filters) * bw + (len(filters) - 1) * gap
        fx = SW / 2 - total / 2
        fy = SH - TH / 2
        for label, col in filters:
            hov = _in_rect(self.mx, self.my, fx, fy - bh_/2, fx + bw, fy + bh_/2)
            bg = (*col, 40) if hov else (*col, 18)
            arcade.draw_lrbt_rectangle_filled(fx, fx + bw, fy - bh_/2, fy + bh_/2, bg)
            arcade.draw_lrbt_rectangle_outline(fx, fx + bw, fy - bh_/2, fy + bh_/2,
                                               (*col, 100 if hov else 60), 1)
            arcade.draw_text(label, fx + bw / 2, fy, (*col, 220),
                             font_size=9, anchor_x="center", anchor_y="center")
            fx += bw + gap

        # Deck name (right side)
        arcade.draw_text(self.deck_name, SW - RW - 12, SH - TH / 2,
                         (*GOLD, 180), font_size=10, italic=True,
                         anchor_x="right", anchor_y="center")

    # ── Deck selector overlay ──────────────────────────────────────────────────

    _SEL_ROW_H  = 52
    _SEL_PAD    = 16
    _SEL_W      = 440

    def _sel_rows(self):
        """Returns list of (deck_dict, x1, y1, x2, y2) for each deck row."""
        rows = []
        pw = self._SEL_W
        px1 = SW / 2 - pw / 2
        row_h = self._SEL_ROW_H
        pad   = self._SEL_PAD
        # top of list area
        top_y = SH / 2 + row_h * len(self._all_decks) / 2
        for i, d in enumerate(self._all_decks):
            y2 = top_y - i * (row_h + 6)
            y1 = y2 - row_h
            rows.append((d, px1, y1, px1 + pw, y2))
        return rows

    def _draw_deck_selector(self):
        # Full-screen dim
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, (10, 12, 18))

        cx = SW / 2
        pw = self._SEL_W

        # Panel
        ph = max(200, len(self._all_decks) * (self._SEL_ROW_H + 6) + 100)
        py1 = SH / 2 - ph / 2
        py2 = SH / 2 + ph / 2
        _rrect_filled(cx - pw/2 - 20, py1 - 20, cx + pw/2 + 20, py2 + 20, 14, (28, 32, 42))
        _rrect_outline(cx - pw/2 - 20, py1 - 20, cx + pw/2 + 20, py2 + 20, 14, (*SEP, 160), 1)

        # Title
        arcade.draw_text("Elegir Deck", cx, py2 + 2, TEXT,
                         font_size=18, bold=True, anchor_x="center", anchor_y="center")

        if not self._all_decks:
            arcade.draw_text("No hay decks guardados.\nCreá uno en el Deck Builder.",
                             cx, SH / 2, DIM, font_size=13,
                             anchor_x="center", anchor_y="center",
                             multiline=True, width=pw, align="center")
        else:
            for d, x1, y1, x2, y2 in self._sel_rows():
                hov = _in_rect(self.mx, self.my, x1, y1, x2, y2)
                bg  = BTN_HOV if hov else BTN
                _rrect_filled(x1, y1, x2, y2, 8, bg)
                border_col = (*BLUE_N, 150) if hov else (*SEP, 80)
                _rrect_outline(x1, y1, x2, y2, 8, border_col, 1)

                name  = d.get('name', '?')
                count = d.get('card_count', 0)
                ry    = (y1 + y2) / 2

                arcade.draw_text(name, x1 + 16, ry + 6, TEXT,
                                 font_size=13, bold=True, anchor_y="center")
                arcade.draw_text(f"{count} cartas", x1 + 16, ry - 10, DIM,
                                 font_size=9, anchor_y="center")

                # Arrow indicator
                arrow_col = (*BLUE_N, 200) if hov else (*DIM, 200)
                arcade.draw_text("▶", x2 - 20, ry, arrow_col,
                                 font_size=12, anchor_x="center", anchor_y="center")

        # Hint
        arcade.draw_text("ESC · Volver al menú", cx, py1 - 10, DIM,
                         font_size=9, anchor_x="center")

    def _handle_deck_select_click(self, x, y):
        for d, x1, y1, x2, y2 in self._sel_rows():
            if _in_rect(x, y, x1, y1, x2, y2):
                self._load_deck(d)
                return

    def _draw_left_panel(self):
        cx  = LW // 2
        # usable panel height excluding top bar
        panel_top = SH - TH

        # Panel background + border
        arcade.draw_lrbt_rectangle_filled(0, LW, 0, SH, PANEL_BG)
        arcade.draw_line(LW, 0, LW, SH, (*SEP, 255), 1)

        # ── Menu button (below top bar) ────────────
        btn_y = panel_top - 20
        hov = _in_rect(self.mx, self.my, 12, btn_y - 16, LW - 12, btn_y + 16)
        _draw_btn(cx, btn_y, LW - 24, 30, "Pausar / Menú", hovered=hov)
        arcade.draw_line(12, btn_y - 26, LW - 12, btn_y - 26, (*SEP, 80), 1)

        # ── Opponent block (top half) ───────────────
        # Avatar — tall portrait box
        av_top  = btn_y - 36
        av_bot  = av_top - 80
        ax1, ax2 = 14, LW - 14
        _rrect_filled(ax1, av_bot, ax2, av_top, 8, (48, 28, 34))
        for exp, al in [(5, 15), (3, 50), (1, 110)]:
            _rrect_outline(ax1-exp, av_bot-exp, ax2+exp, av_top+exp,
                           8+exp, (*RED_N, al), 1)
        _rrect_outline(ax1, av_bot, ax2, av_top, 8, (*RED_N, 200), 2)
        arcade.draw_text("?", cx, (av_bot + av_top) // 2, (*RED_N, 160),
                         font_size=28, bold=True,
                         anchor_x="center", anchor_y="center")

        # LP
        lp_y = av_bot - 20
        _neon_lp(cx, lp_y, self.opponent_lp, RED_N)

        # Mano / Cementerio inline
        mc_y = lp_y - 22
        arcade.draw_text(
            f"Mano: {self.opponent_hand}   Cementerio: {self.opponent_gy}",
            cx, mc_y, (*RED_N, 180), font_size=9,
            anchor_x="center", anchor_y="center"
        )

        sep1 = mc_y - 14
        arcade.draw_line(12, sep1, LW - 12, sep1, (*SEP, 70), 1)

        # ── Phase strip ────────────────────────────
        ph_y    = sep1 - 18
        pw_tot  = LW - 20
        pill_w  = (pw_tot - (len(_PHASES) - 1) * 4) / len(_PHASES)
        pill_h  = 20
        for i, ph in enumerate(_PHASES):
            px1 = 10 + i * (pill_w + 4)
            px2 = px1 + pill_w
            active = (ph == self.current_phase)
            if active:
                # gold glow + fill
                for exp, al in [(4, 10), (2, 30), (1, 60)]:
                    arcade.draw_lrbt_rectangle_filled(
                        px1 - exp, px2 + exp, ph_y - pill_h//2 - exp,
                        ph_y + pill_h//2 + exp, (*GOLD, al))
                _rrect_filled(px1, ph_y - pill_h//2, px2, ph_y + pill_h//2,
                              5, (58, 50, 16))
                _rrect_outline(px1, ph_y - pill_h//2, px2, ph_y + pill_h//2,
                               5, (*GOLD, 230), 1)
            else:
                _rrect_filled(px1, ph_y - pill_h//2, px2, ph_y + pill_h//2,
                              5, (34, 37, 46))
                _rrect_outline(px1, ph_y - pill_h//2, px2, ph_y + pill_h//2,
                               5, (*SEP, 100), 1)
            arcade.draw_text(ph, (px1 + px2) / 2, ph_y,
                             GOLD if active else DIM,
                             font_size=7, bold=active,
                             anchor_x="center", anchor_y="center")

        # phase name label
        ph_name = _PHASE_LABELS.get(self.current_phase, self.current_phase)
        arcade.draw_text(ph_name, cx, ph_y - pill_h//2 - 10,
                         (*GOLD, 200), font_size=8, anchor_x="center")

        sep2 = ph_y - pill_h//2 - 22
        arcade.draw_line(12, sep2, LW - 12, sep2, (*SEP, 70), 1)

        # ── Player block (bottom half) ──────────────
        # Mano / Cementerio inline
        mc2_y = sep2 - 16
        arcade.draw_text(
            f"Mano: {self.player_hand}   Cementerio: {self.player_gy}",
            cx, mc2_y, (*BLUE_N, 180), font_size=9,
            anchor_x="center", anchor_y="center"
        )

        # LP
        lp2_y = mc2_y - 22
        _neon_lp(cx, lp2_y, self.player_lp, BLUE_N)

        # Avatar — tall portrait box
        av2_top = lp2_y - 16
        av2_bot = av2_top - 80
        _rrect_filled(ax1, av2_bot, ax2, av2_top, 8, (24, 34, 50))
        for exp, al in [(5, 15), (3, 50), (1, 110)]:
            _rrect_outline(ax1-exp, av2_bot-exp, ax2+exp, av2_top+exp,
                           8+exp, (*BLUE_N, al), 1)
        _rrect_outline(ax1, av2_bot, ax2, av2_top, 8, (*BLUE_N, 200), 2)
        arcade.draw_text("J", cx, (av2_bot + av2_top) // 2, (*BLUE_N, 180),
                         font_size=28, bold=True,
                         anchor_x="center", anchor_y="center")

        sep3 = av2_bot - 10
        arcade.draw_line(12, sep3, LW - 12, sep3, (*SEP, 70), 1)

        # ── Action buttons ─────────────────────────
        btn_area_mid = sep3 / 2
        hov_bat = _in_rect(self.mx, self.my, 12, btn_area_mid + 4,
                           LW - 12, btn_area_mid + 46)
        hov_pas = _in_rect(self.mx, self.my, 12, btn_area_mid - 46,
                           LW - 12, btn_area_mid - 4)

        _draw_btn(cx, btn_area_mid + 25, LW - 24, 36, "Fase de Batalla",
                  hovered=hov_bat, active=True, color=BTN_ACT)
        _draw_btn(cx, btn_area_mid - 25, LW - 24, 36, "Pasar Turno",
                  hovered=hov_pas, color=GOLD)

    def _draw_right_panel(self):
        rx = SW - RW    # left edge of right panel
        cx = rx + RW // 2

        # Background
        arcade.draw_lrbt_rectangle_filled(rx, SW, 0, SH, PANEL_BG)
        arcade.draw_line(rx, 0, rx, SH, (*SEP, 200), 1)

        # Header (below top bar)
        hdr_y = SH - TH - 18
        arcade.draw_text("Detalles de Carta", cx, hdr_y, TEXT,
                         font_size=12, bold=True, anchor_x="center")
        arcade.draw_line(rx + 10, hdr_y - 14, SW - 10, hdr_y - 14, (*SEP, 100), 1)

        # ── Card detail ───────────────────────────
        img_h  = 210
        img_y  = hdr_y - 14 - img_h // 2 - 6   # center of image area

        cdata = self.hover_card.card_data if self.hover_card else None

        if cdata:
            ctype  = cdata.get('card_type', 'MONSTER')
            attr   = cdata.get('attribute', '')
            tc     = {'MONSTER': C_MONSTER, 'SPELL': C_SPELL, 'TRAP': C_TRAP}.get(ctype, DIM)

            # Card image — load full-size for the detail panel
            ix1, ix2 = rx + 14, SW - 14
            iy1, iy2 = img_y - img_h // 2, img_y + img_h // 2
            img_name = cdata.get('image_name', '')
            detail_tex = self._get_detail_tex(img_name) if img_name else None
            if detail_tex:
                # Fit image preserving aspect ratio, centered in available area
                avail_w = ix2 - ix1
                avail_h = iy2 - iy1
                scale   = min(avail_w / detail_tex.width, avail_h / detail_tex.height)
                draw_w  = detail_tex.width  * scale
                draw_h  = detail_tex.height * scale
                dcx     = (ix1 + ix2) / 2
                dcy     = (iy1 + iy2) / 2
                dx1 = dcx - draw_w / 2
                dx2 = dcx + draw_w / 2
                dy1 = dcy - draw_h / 2
                dy2 = dcy + draw_h / 2
                # outer glow rings matching card type color
                for exp, al in [(5, 20), (3, 55), (1, 110)]:
                    arcade.draw_lrbt_rectangle_filled(
                        dx1 - exp, dx2 + exp, dy1 - exp, dy2 + exp, (*tc, al))
                arcade.draw_texture_rect(
                    detail_tex, arcade.LRBT(dx1, dx2, dy1, dy2))
            else:
                arcade.draw_lrbt_rectangle_filled(ix1, ix2, iy1, iy2, (28, 30, 40))
                for exp, al in [(4, 40), (2, 100), (0, 200)]:
                    _rrect_outline(ix1 - exp, iy1 - exp, ix2 + exp, iy2 + exp,
                                   8, (*tc, al), 1)
                arcade.draw_text(ctype, cx, img_y, (*tc, 80), font_size=22,
                                 bold=True, anchor_x="center", anchor_y="center")

            # Name
            ny = img_y - img_h // 2 - 18
            arcade.draw_text(cdata.get('name', '?'), rx + 12, ny, TEXT,
                             font_size=13, bold=True,
                             width=RW - 24, multiline=False,
                             anchor_y="center")

            # Type badge
            badge_x = SW - 12
            badge_lbl = cdata.get('type') or ctype
            arcade.draw_text(badge_lbl[:18], badge_x, ny, (*tc, 200),
                             font_size=9, anchor_x="right", anchor_y="center",
                             italic=True)

            # ── Stat grid ─────────────────────────────
            grid_top = ny - 14
            arcade.draw_line(rx + 10, grid_top, SW - 10, grid_top, (*SEP, 60), 1)

            def _stat_cell(gx1, gy_center, icon, icon_col, label, value, val_col=TEXT):
                """Icon + label + value in a small pill cell."""
                _rrect_filled(gx1, gy_center - 13, gx1 + cell_w, gy_center + 13, 6,
                              (30, 33, 42))
                _rrect_outline(gx1, gy_center - 13, gx1 + cell_w, gy_center + 13, 6,
                               (*SEP, 60), 1)
                arcade.draw_text(icon, gx1 + 10, gy_center, icon_col,
                                 font_size=10, anchor_x="center", anchor_y="center")
                arcade.draw_text(label, gx1 + 22, gy_center + 4, DIM,
                                 font_size=7, anchor_y="center")
                arcade.draw_text(str(value), gx1 + 22, gy_center - 5, val_col,
                                 font_size=9, bold=True, anchor_y="center",
                                 width=cell_w - 26)

            pad_x   = rx + 10
            cell_w  = (RW - 24) // 2 - 2
            row1_y  = grid_top - 22
            row2_y  = grid_top - 50

            if ctype == 'MONSTER':
                lvl      = cdata.get('level') or 0
                attr_col = _ATTR_COLORS.get(attr, DIM)

                # Row 1: Tipo | Atributo
                _stat_cell(pad_x,              row1_y, "◈", tc,       "TIPO", ctype, tc)
                _stat_cell(pad_x + cell_w + 4, row1_y, "●", attr_col, "ATR",  attr or '-', attr_col)

                # Row 2: Nivel | ATK | DEF  (3 narrow cells)
                narrow_w = (RW - 28) // 3
                n_y = row2_y

                # Nivel cell (stars compact)
                _rrect_filled(pad_x, n_y - 13, pad_x + narrow_w, n_y + 13, 6, (30, 33, 42))
                _rrect_outline(pad_x, n_y - 13, pad_x + narrow_w, n_y + 13, 6, (*SEP, 60), 1)
                arcade.draw_text("★", pad_x + 10, n_y, GOLD, font_size=10,
                                 anchor_x="center", anchor_y="center")
                arcade.draw_text("NVL", pad_x + 22, n_y + 4, DIM, font_size=7, anchor_y="center")
                arcade.draw_text(str(int(lvl)), pad_x + 22, n_y - 5, GOLD,
                                 font_size=9, bold=True, anchor_y="center")

                # ATK cell
                ax = pad_x + narrow_w + 3
                _rrect_filled(ax, n_y - 13, ax + narrow_w, n_y + 13, 6, (40, 24, 24))
                _rrect_outline(ax, n_y - 13, ax + narrow_w, n_y + 13, 6, (*(255,100,100), 60), 1)
                arcade.draw_text("⚔", ax + 10, n_y, (255, 120, 120), font_size=10,
                                 anchor_x="center", anchor_y="center")
                arcade.draw_text("ATK", ax + 22, n_y + 4, DIM, font_size=7, anchor_y="center")
                arcade.draw_text(str(cdata.get('atk', '?')), ax + 22, n_y - 5,
                                 (255, 140, 140), font_size=9, bold=True, anchor_y="center")

                # DEF cell
                dx = ax + narrow_w + 3
                _rrect_filled(dx, n_y - 13, dx + narrow_w, n_y + 13, 6, (22, 28, 50))
                _rrect_outline(dx, n_y - 13, dx + narrow_w, n_y + 13, 6, (*(100,140,255), 60), 1)
                arcade.draw_text("🛡", dx + 10, n_y, (120, 160, 255), font_size=9,
                                 anchor_x="center", anchor_y="center")
                arcade.draw_text("DEF", dx + 22, n_y + 4, DIM, font_size=7, anchor_y="center")
                arcade.draw_text(str(cdata.get('def', '?')), dx + 22, n_y - 5,
                                 (140, 170, 255), font_size=9, bold=True, anchor_y="center")

                effect_y = row2_y - 22
            else:
                # Non-monster: just type + subtype cells
                subtype = cdata.get('type', ctype)
                _stat_cell(pad_x,              row1_y, "◈", tc, "TIPO",    ctype,   tc)
                _stat_cell(pad_x + cell_w + 4, row1_y, "◆", DIM, "SUBTIPO", subtype, DIM)
                effect_y = row1_y - 24

            # Effect text
            arcade.draw_line(rx + 10, effect_y + 4, SW - 10, effect_y + 4,
                             (*SEP, 60), 1)
            effect = cdata.get('text', '')
            if effect:
                arcade.draw_text(effect, rx + 12, effect_y - 4,
                                 (175, 178, 185), font_size=9,
                                 width=RW - 24, multiline=True,
                                 anchor_y="top")
        else:
            # Placeholder
            arcade.draw_lrbt_rectangle_filled(rx + 24, SW - 24,
                                              img_y - img_h//2, img_y + img_h//2,
                                              (25, 27, 36))
            _rrect_outline(rx + 24, img_y - img_h//2, SW - 24, img_y + img_h//2,
                           8, (*SEP, 80), 1)
            arcade.draw_text("Pasa el cursor\nsobre una carta",
                             cx, img_y, DIM, font_size=11,
                             anchor_x="center", anchor_y="center",
                             multiline=True, width=RW - 48, align="center")

        # ── Duel Log ──────────────────────────────
        log_y = 190
        arcade.draw_line(rx + 10, log_y, SW - 10, log_y, (*SEP, 100), 1)
        arcade.draw_text("Registro de Duelo", cx, log_y - 16, TEXT,
                         font_size=11, bold=True, anchor_x="center")

        for i, (msg, col) in enumerate(reversed(self.duel_log[-6:])):
            entry_y = log_y - 36 - i * 20
            if entry_y < 16:
                break
            # subtle row bg on alternating entries
            if i % 2 == 0:
                arcade.draw_lrbt_rectangle_filled(
                    rx + 8, SW - 8, entry_y - 8, entry_y + 10, (28, 30, 38))
            arcade.draw_text(f"• {msg}", rx + 14, entry_y,
                             col, font_size=9, anchor_y="center",
                             width=RW - 28)

    def _draw_zone(self, zone):
        fill, outline_rgb = _zone_style(zone.name)
        x1 = zone.x - CW / 2
        y1 = zone.y - CH / 2
        x2 = zone.x + CW / 2
        y2 = zone.y + CH / 2

        arcade.draw_lrbt_rectangle_filled(x1, x2, y1, y2, fill)

        al = 220 if zone.is_full() else 150
        lw = 2.0 if zone.is_full() else 1.5
        _rrect_outline(x1, y1, x2, y2, 4, (*outline_rgb, al), lw)

        # Zone label in zone color, dimmed
        arcade.draw_text(_zone_abbr(zone.name),
                         zone.x, zone.y, (*outline_rgb, 130),
                         font_size=8, bold=True,
                         anchor_x="center", anchor_y="center")

    # ── Events ────────────────────────────────────────────────────────────────

    def _cards_at(self, x, y):
        return [c for c in self.card_list
                if abs(c.center_x - x) <= CW / 2 and abs(c.center_y - y) <= CH / 2]

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y
        if self.held_card:
            self.held_card.center_x += dx
            self.held_card.center_y += dy
        else:
            for c in self.card_list:
                c.hovered = False
            cards_at = [c for c in self.card_list if c.collides_with_point((x, y))]
            self.hover_card = cards_at[-1] if cards_at else None
            if self.hover_card:
                self.hover_card.hovered = True

    def on_mouse_press(self, x, y, button, modifiers):
        if self._selecting:
            self._handle_deck_select_click(x, y)
            return

        # Menu button
        if _in_rect(x, y, 12, SH - 48, LW - 12, SH - 8):
            self._go_menu()
            return

        cards_at = [c for c in self.card_list if c.collides_with_point((x, y))]
        if not cards_at:
            return

        target = cards_at[-1]
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.held_card = target
            self.held_card.is_held = True
            # Store the unmodified base position to prevent endless hover-climbing
            self.held_card_original_position = (target.center_x, target._base_y)
            if self.held_card.current_zone:
                self.held_card.current_zone.remove_card(self.held_card)
            self.card_list.remove(self.held_card)
            self.card_list.append(self.held_card)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            target.in_attack_position = not target.in_attack_position
            target.angle = 0 if target.in_attack_position else 90

    def on_mouse_release(self, x, y, button, modifiers):
        if self._selecting:
            return
        if button != arcade.MOUSE_BUTTON_LEFT or not self.held_card:
            return
        zone = self.board_manager.get_zone_at(x, y)
        if zone and not zone.is_full():
            self.held_card.position = (zone.x, zone.y)
            self.held_card._base_y = zone.y
            self.held_card.current_zone = zone
            zone.add_card(self.held_card)
            name = getattr(self.held_card, 'name', '?')
            self._log(f"Jugador colocó {name} en {zone.name}", BLUE_N)
        else:
            self.held_card.position = self.held_card_original_position
            if self.held_card_original_position:
                self.held_card._base_y = self.held_card_original_position[1]
            if self.held_card.current_zone:
                self.held_card.current_zone.add_card(self.held_card)
        self.held_card.is_held = False
        self.held_card = None

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            if self._selecting:
                self._go_menu()
            else:
                self._go_menu()

    def _log(self, msg: str, color=None):
        self.duel_log.append((msg, color or DIM))
        if len(self.duel_log) > 50:
            self.duel_log.pop(0)

    def _go_menu(self):
        from menu_view import MenuView
        self.window.show_view(MenuView())

    def on_hide_view(self):
        pass
