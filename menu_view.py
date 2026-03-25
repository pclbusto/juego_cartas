import arcade
import constants
from ui_prueba_concepto import ShaderButton, ShaderPanel

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


# --- Legacy drawing helpers removed, using ShaderButton ---


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
        ctx = self.window.ctx
        self.objs = []
        for action, label, cx, cy in self._btn_positions():
            btn = ShaderButton(ctx, cx, cy, BTN_W, BTN_H, label)
            # Guardamos la acción en el objeto para facilitar el click
            btn.action = action
            self.objs.append(btn)

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
        for btn in self.objs:
            btn.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y
        for btn in self.objs:
            btn.on_mouse_motion(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        for btn in self.objs:
            if btn.contains(x, y):
                self._dispatch(btn.action)
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
