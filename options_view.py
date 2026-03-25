import arcade
import constants
from database import DatabaseManager

SW = constants.SCREEN_WIDTH
SH = constants.SCREEN_HEIGHT

# ── Colors (same palette) ─────────────────────────────────────────────────────
BG      = (26, 26, 26)
PANEL   = (38, 38, 38)
SEP     = (60, 60, 60)
TEXT    = (225, 225, 225)
DIM     = (120, 120, 120)
GOLD    = (255, 200, 50)
BLUE    = (30, 130, 255)
GREEN   = (50, 190, 80)
BTN     = (55, 55, 55)
BTN_HOV = (70, 70, 70)
BTN_ACT = (40, 100, 200)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    arcade.draw_line(x1 + r, y1,  x2 - r, y1,  color, lw)
    arcade.draw_line(x1 + r, y2,  x2 - r, y2,  color, lw)
    arcade.draw_line(x1, y1 + r,  x1, y2 - r,  color, lw)
    arcade.draw_line(x2, y1 + r,  x2, y2 - r,  color, lw)
    d = r * 2
    arcade.draw_arc_outline(x1+r, y1+r, d, d, color, 180, 270, lw)
    arcade.draw_arc_outline(x2-r, y1+r, d, d, color, 270, 360, lw)
    arcade.draw_arc_outline(x2-r, y2-r, d, d, color,   0,  90, lw)
    arcade.draw_arc_outline(x1+r, y2-r, d, d, color,  90, 180, lw)


def _draw_btn(cx, cy, w, h, label, hovered=False, active=False):
    x1, x2 = cx - w // 2, cx + w // 2
    y1, y2 = cy - h // 2, cy + h // 2
    bg = BTN_ACT if active else (BTN_HOV if hovered else BTN)
    _rrect_filled(x1, y1, x2, y2, 7, bg)
    border = (*BLUE, 180) if active else (*SEP, 120)
    _rrect_outline(x1, y1, x2, y2, 7, border, 1)
    arcade.draw_text(label, cx, cy, TEXT, font_size=12,
                     anchor_x="center", anchor_y="center")


# ── Settings definitions ──────────────────────────────────────────────────────

# (db_value, display_label, ram_hint)
THUMB_OPTIONS = [
    (None,   "Ilimitado",  "RAM: sin límite"),
    ("2000", "2 000",      "RAM: ~90 MB"),
    ("1000", "1 000",      "RAM: ~45 MB"),
    ("400",  "400",        "RAM: ~18 MB"),
    ("200",  "200",        "RAM: ~9 MB"),
]

FREE_ON_EXIT_OPTIONS = [
    ("0", "Mantener en memoria",  "Re-entrada más rápida"),
    ("1", "Liberar al salir",     "GPU libre al volver al menú"),
]

RES_OPTIONS = [
    ("1280x720",  "HD",      "1280 x 720"),
    ("1920x1080", "FHD",     "1920 x 1080"),
    ("2560x1080", "2K 21:9", "2560 x 1080"),
]

class OptionsView(arcade.View):

    def __init__(self):
        super().__init__()
        self.db           = DatabaseManager()
        self.mx = self.my = 0
        self._thumb_val   = None   # current db value for thumb_limit
        self._free_val    = "0"    # current db value for free_on_exit
        self._res_val     = "1280x720"

    def on_show_view(self):
        self._thumb_val = self.db.get_setting("thumb_limit", None)
        self._free_val  = self.db.get_setting("free_on_exit", "0")
        self._res_val   = self.db.get_setting("resolution", "1280x720")

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _thumb_btn_rect(self, i):
        """(cx, cy, w, h) for the i-th thumb option button."""
        w, h  = 130, 36
        gap   = 12
        total = len(THUMB_OPTIONS) * w + (len(THUMB_OPTIONS) - 1) * gap
        x0    = SW // 2 - total // 2 + w // 2
        cx    = x0 + i * (w + gap)
        cy    = SH // 2 + 60
        return cx, cy, w, h

    def _free_btn_rect(self, i):
        w, h  = 220, 36
        gap   = 16
        total = len(FREE_ON_EXIT_OPTIONS) * w + (len(FREE_ON_EXIT_OPTIONS) - 1) * gap
        x0    = SW // 2 - total // 2 + w // 2
        cx    = x0 + i * (w + gap)
        cy    = SH // 2 - 30
        return cx, cy, w, h
        
    def _res_btn_rect(self, i):
        w, h  = 160, 36
        gap   = 12
        total = len(RES_OPTIONS) * w + (len(RES_OPTIONS) - 1) * gap
        x0    = SW // 2 - total // 2 + w // 2
        cx    = x0 + i * (w + gap)
        cy    = SH // 2 - 120
        return cx, cy, w, h

    def _back_rect(self):
        return SW // 2, SH // 2 - 200, 160, 38

    # ── Draw ──────────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear()

        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG)

        # Top bar
        arcade.draw_lrbt_rectangle_filled(0, SW, SH - 60, SH, PANEL)
        arcade.draw_line(0, SH - 60, SW, SH - 60, SEP, 1)
        arcade.draw_text("Opciones", SW // 2, SH - 30,
                         GOLD, font_size=20, bold=True,
                         anchor_x="center", anchor_y="center")

        # Bottom bar
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, 30, PANEL)
        arcade.draw_line(0, 30, SW, 30, SEP, 1)

        # ── Thumbnail limit section ──
        section_y = SH // 2 + 105
        arcade.draw_text("Límite de miniaturas en memoria",
                         SW // 2, section_y,
                         TEXT, font_size=14, bold=True, anchor_x="center")
        arcade.draw_text(
            "Cuántas imágenes de carta se mantienen cargadas al navegar el Deck Builder.",
            SW // 2, section_y - 22,
            DIM, font_size=10, anchor_x="center"
        )

        for i, (val, label, hint) in enumerate(THUMB_OPTIONS):
            cx, cy, w, h = self._thumb_btn_rect(i)
            active  = (self._thumb_val == val)
            hovered = _in_rect(self.mx, self.my,
                               cx - w//2, cy - h//2, cx + w//2, cy + h//2)
            _draw_btn(cx, cy, w, h, label, hovered=hovered, active=active)
            # RAM hint below each button
            hint_col = (*GREEN, 200) if active else (*DIM, 180)
            arcade.draw_text(hint, cx, cy - h//2 - 12, hint_col,
                             font_size=8, anchor_x="center")

        # ── Free on exit section ──
        section2_y = SH // 2 + 15
        arcade.draw_text("Al salir del Deck Builder",
                         SW // 2, section2_y,
                         TEXT, font_size=14, bold=True, anchor_x="center")
        arcade.draw_text(
            "Controla si las texturas GPU se liberan al volver al menú.",
            SW // 2, section2_y - 22,
            DIM, font_size=10, anchor_x="center"
        )

        for i, (val, label, hint) in enumerate(FREE_ON_EXIT_OPTIONS):
            cx, cy, w, h = self._free_btn_rect(i)
            active  = (self._free_val == val)
            hovered = _in_rect(self.mx, self.my,
                               cx - w//2, cy - h//2, cx + w//2, cy + h//2)
            _draw_btn(cx, cy, w, h, label, hovered=hovered, active=active)
            hint_col = (*GREEN, 200) if active else (*DIM, 180)
            arcade.draw_text(hint, cx, cy - h//2 - 12, hint_col,
                             font_size=8, anchor_x="center")

        # ── Resolution section ──
        section3_y = SH // 2 - 75
        arcade.draw_text("Resolución de Pantalla",
                         SW // 2, section3_y,
                         TEXT, font_size=14, bold=True, anchor_x="center")
        arcade.draw_text(
            "Selecciona el tamaño de la ventana. (Requiere reiniciar el juego).",
            SW // 2, section3_y - 22,
            DIM, font_size=10, anchor_x="center"
        )

        for i, (val, label, hint) in enumerate(RES_OPTIONS):
            cx, cy, w, h = self._res_btn_rect(i)
            active  = (self._res_val == val)
            hovered = _in_rect(self.mx, self.my,
                               cx - w//2, cy - h//2, cx + w//2, cy + h//2)
            _draw_btn(cx, cy, w, h, label, hovered=hovered, active=active)
            hint_col = (*GREEN, 200) if active else (*DIM, 180)
            arcade.draw_text(hint, cx, cy - h//2 - 12, hint_col, font_size=8, anchor_x="center")

        # Back button
        cx, cy, w, h = self._back_rect()
        hov = _in_rect(self.mx, self.my, cx - w//2, cy - h//2, cx + w//2, cy + h//2)
        _draw_btn(cx, cy, w, h, "← Volver", hovered=hov)

    # ── Events ────────────────────────────────────────────────────────────────

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y

    def on_mouse_press(self, x, y, button, modifiers):
        # Thumb limit buttons
        for i, (val, _, _) in enumerate(THUMB_OPTIONS):
            cx, cy, w, h = self._thumb_btn_rect(i)
            if _in_rect(x, y, cx - w//2, cy - h//2, cx + w//2, cy + h//2):
                self._thumb_val = val
                self.db.set_setting("thumb_limit", val)
                return

        # Free on exit buttons
        for i, (val, _, _) in enumerate(FREE_ON_EXIT_OPTIONS):
            cx, cy, w, h = self._free_btn_rect(i)
            if _in_rect(x, y, cx - w//2, cy - h//2, cx + w//2, cy + h//2):
                self._free_val = val
                self.db.set_setting("free_on_exit", val)
                return

        # Resolution buttons
        for i, (val, _, _) in enumerate(RES_OPTIONS):
            cx, cy, w, h = self._res_btn_rect(i)
            if _in_rect(x, y, cx - w//2, cy - h//2, cx + w//2, cy + h//2):
                self._res_val = val
                self.db.set_setting("resolution", val)
                return

        # Back
        cx, cy, w, h = self._back_rect()
        if _in_rect(x, y, cx - w//2, cy - h//2, cx + w//2, cy + h//2):
            self._go_back()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            self._go_back()

    def _go_back(self):
        from menu_view import MenuView
        self.window.show_view(MenuView())
