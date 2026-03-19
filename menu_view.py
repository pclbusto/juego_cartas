import arcade
import constants

SW = constants.SCREEN_WIDTH
SH = constants.SCREEN_HEIGHT

# ── Colors (same palette as deck_builder_view) ────────────────────────────────
BG      = (26, 26, 26)
PANEL   = (38, 38, 38)
SEP     = (60, 60, 60)
TEXT    = (225, 225, 225)
DIM     = (120, 120, 120)
GOLD    = (255, 200, 50)
BLUE    = (30, 130, 255)
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
    arcade.draw_text(label, cx, cy, TEXT, font_size=13,
                     anchor_x="center", anchor_y="center")


# ── View ──────────────────────────────────────────────────────────────────────

BTN_W = 260
BTN_H = 44
BTN_GAP = 16

_BUTTONS = [
    ("deck_builder", "Deck Builder"),
    ("play",         "Jugar"),
    ("manage_decks", "Gestionar Decks"),
    ("options",      "Opciones"),
    ("quit",         "Salir"),
]


class MenuView(arcade.View):

    def __init__(self):
        super().__init__()
        self.mx = self.my = 0

    def on_show_view(self):
        pass

    def _btn_positions(self):
        """Returns list of (action, label, cx, cy)."""
        total_h = len(_BUTTONS) * BTN_H + (len(_BUTTONS) - 1) * BTN_GAP
        start_y = SH // 2 + total_h // 2 - BTN_H // 2
        cx = SW // 2
        result = []
        for i, (action, label) in enumerate(_BUTTONS):
            cy = start_y - i * (BTN_H + BTN_GAP)
            result.append((action, label, cx, cy))
        return result

    def on_draw(self):
        self.clear()

        # Background
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG)

        # Subtle top bar
        arcade.draw_lrbt_rectangle_filled(0, SW, SH - 60, SH, PANEL)
        arcade.draw_line(0, SH - 60, SW, SH - 60, SEP, 1)

        # Subtle bottom bar
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, 30, PANEL)
        arcade.draw_line(0, 30, SW, 30, SEP, 1)

        # Title
        arcade.draw_text(
            "YU-GI-OH  ·  Card Game",
            SW // 2, SH - 30,
            GOLD, font_size=22, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # Version
        arcade.draw_text(
            "v1.0 — Deck Builder Edition",
            SW // 2, 15,
            DIM, font_size=10,
            anchor_x="center", anchor_y="center"
        )

        # Center card-game logo area (decorative separator lines)
        lx1, lx2 = SW // 2 - 160, SW // 2 + 160
        logo_y = SH // 2 + 160
        arcade.draw_line(lx1, logo_y, lx2, logo_y, (*SEP, 80), 1)

        # Buttons
        for action, label, cx, cy in self._btn_positions():
            hov = _in_rect(self.mx, self.my,
                           cx - BTN_W // 2, cy - BTN_H // 2,
                           cx + BTN_W // 2, cy + BTN_H // 2)
            _draw_btn(cx, cy, BTN_W, BTN_H, label, hovered=hov)

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y

    def on_mouse_press(self, x, y, button, modifiers):
        for action, label, cx, cy in self._btn_positions():
            if _in_rect(x, y,
                        cx - BTN_W // 2, cy - BTN_H // 2,
                        cx + BTN_W // 2, cy + BTN_H // 2):
                self._dispatch(action)
                return

    def _dispatch(self, action):
        if action == "deck_builder":
            from deck_builder_view import DeckBuilderView
            v = DeckBuilderView()
            v.setup()
            self.window.show_view(v)
        elif action == "play":
            from game_view import GameView
            v = GameView()
            v.setup()
            self.window.show_view(v)
        elif action == "manage_decks":
            from deck_management_view import DeckManagementView
            v = DeckManagementView()
            v.setup()
            self.window.show_view(v)
        elif action == "options":
            from options_view import OptionsView
            self.window.show_view(OptionsView())
        elif action == "quit":
            arcade.exit()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            arcade.exit()
