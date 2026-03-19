import arcade
import constants
from card import Card
from zones import BoardManager
from database import DatabaseManager

SW = constants.SCREEN_WIDTH
SH = constants.SCREEN_HEIGHT
CW = constants.CARD_WIDTH
CH = constants.CARD_HEIGHT

TOOLBAR_H   = 50
STATUSBAR_H = 28

# ── Colors ────────────────────────────────────────────────────────────────────
BOARD_BG = (18, 28, 45)
PANEL    = (38, 38, 38)
SEP      = (60, 60, 60)
TEXT     = (225, 225, 225)
DIM      = (120, 120, 120)
GOLD     = (255, 200, 50)
BLUE     = (30, 130, 255)
BTN      = (55, 55, 55)
BTN_HOV  = (70, 70, 70)

# Zone visual style per type: (fill_rgba, outline_rgb)
_ZONE_STYLES = {
    "Monster":  ((55, 22,  8, 150), (220, 110,  50)),
    "Spell":    (( 8, 28, 65, 150), ( 55, 135, 230)),
    "Pendulum": ((44, 12, 65, 150), (175,  75, 220)),
    "Field":    ((12, 50, 18, 150), ( 75, 190,  80)),
    "GY":       ((35, 35, 35, 150), (140, 140, 140)),
    "Deck":     ((22, 22, 50, 150), ( 95,  95, 180)),
    "Extra":    ((22, 22, 50, 150), ( 95,  95, 180)),
}

_ZONE_LABELS = {
    "Monster":  "MON",
    "Spell":    "S/T",
    "Pendulum": "PEN",
    "Field":    "FLD",
    "GY":       "GY",
    "Deck":     "DECK",
    "Extra":    "EX",
}


def _zone_style(name):
    for key in _ZONE_STYLES:
        if key in name:
            return _ZONE_STYLES[key]
    return ((40, 40, 40, 150), (100, 100, 100))


def _zone_label(name):
    for key in _ZONE_LABELS:
        if key in name:
            return _ZONE_LABELS[key]
    return name.split()[0][:3].upper()


# ── UI helpers (same as menu_view / deck_builder_view) ────────────────────────

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


def _draw_btn(cx, cy, w, h, label, hovered=False):
    x1, x2 = cx - w // 2, cx + w // 2
    y1, y2 = cy - h // 2, cy + h // 2
    _rrect_filled(x1, y1, x2, y2, 7, BTN_HOV if hovered else BTN)
    _rrect_outline(x1, y1, x2, y2, 7, (*SEP, 120), 1)
    arcade.draw_text(label, cx, cy, TEXT, font_size=11,
                     anchor_x="center", anchor_y="center")


# ── View ──────────────────────────────────────────────────────────────────────

class GameView(arcade.View):

    def __init__(self):
        super().__init__()
        self.db             = DatabaseManager()
        self.board_manager  = BoardManager()
        self.card_list      = arcade.SpriteList()
        self.held_card      = None
        self.held_card_original_position = None
        self.deck_name      = ""
        self.mx = self.my   = 0

    def setup(self):
        self.card_list.clear()

        decks = self.db.get_all_decks()
        if not decks:
            return

        deck      = decks[0]
        self.deck_name  = deck['name']
        deck_cards = self.db.get_deck_cards(deck['id'])

        if deck_cards:
            flat = []
            for cd in deck_cards:
                for _ in range(cd.get('quantity', 1)):
                    flat.append(cd)

            for i, cd in enumerate(flat[:7]):
                card = Card(name=cd.get('name', '???'),
                            card_type=cd.get('card_type', 'Monster'))
                card.position = (SW // 2 - 330 + 110 * i, STATUSBAR_H + 55)
                self.card_list.append(card)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear()

        # Board background
        arcade.draw_lrbt_rectangle_filled(0, SW, STATUSBAR_H, SH - TOOLBAR_H, BOARD_BG)

        # Subtle grid lines on board
        for gx in range(0, SW, 110):
            arcade.draw_line(gx, STATUSBAR_H, gx, SH - TOOLBAR_H, (*SEP, 18), 1)
        for gy in range(STATUSBAR_H, SH - TOOLBAR_H, 110):
            arcade.draw_line(0, gy, SW, gy, (*SEP, 18), 1)

        # Zones
        for zone in self.board_manager.zones:
            self._draw_zone(zone)

        # Cards
        self.card_list.draw()

        # Held card highlight ring
        if self.held_card:
            hx, hy = self.held_card.center_x, self.held_card.center_y
            x1, y1 = hx - CW // 2 - 4, hy - CH // 2 - 4
            x2, y2 = hx + CW // 2 + 4, hy + CH // 2 + 4
            _rrect_outline(x1, y1, x2, y2, 6, (*GOLD, 200), 2)

        # Toolbar
        arcade.draw_lrbt_rectangle_filled(0, SW, SH - TOOLBAR_H, SH, PANEL)
        arcade.draw_line(0, SH - TOOLBAR_H, SW, SH - TOOLBAR_H, SEP, 1)
        arcade.draw_text(self.deck_name or "Sin deck",
                         20, SH - TOOLBAR_H + 16, GOLD, font_size=15, bold=True)

        tby = SH - TOOLBAR_H // 2
        hov = _in_rect(self.mx, self.my, SW - 130, tby - 16, SW - 20, tby + 16)
        _draw_btn(SW - 75, tby, 110, 32, "← Menú", hovered=hov)

        # Status bar
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, STATUSBAR_H, PANEL)
        arcade.draw_line(0, STATUSBAR_H, SW, STATUSBAR_H, SEP, 1)
        arcade.draw_text(
            "Click izq: agarrar  ·  Soltar en zona: colocar  ·  Click der: rotar  ·  ESC: menú",
            SW // 2, STATUSBAR_H // 2,
            DIM, font_size=9, anchor_x="center", anchor_y="center"
        )

        # Hand label
        hand_y = STATUSBAR_H + 55
        arcade.draw_text("MANO", 20, hand_y + CH // 2 + 6, DIM, font_size=9, bold=True)

    def _draw_zone(self, zone):
        fill, outline_rgb = _zone_style(zone.name)
        left   = zone.x - CW / 2
        bottom = zone.y - CH / 2
        right  = zone.x + CW / 2
        top    = zone.y + CH / 2

        # Fill
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, fill)

        # Outline — brighter if full
        alpha  = 220 if zone.is_full() else 160
        lw     = 2   if zone.is_full() else 1.5
        _rrect_outline(left, bottom, right, top, 4,
                       (*outline_rgb, alpha), lw)

        # Label
        label_col = (*outline_rgb, 200)
        arcade.draw_text(_zone_label(zone.name),
                         zone.x, zone.y, label_col,
                         font_size=9, bold=True,
                         anchor_x="center", anchor_y="center")

    # ── Events ────────────────────────────────────────────────────────────────

    def on_mouse_motion(self, x, y, dx, dy):
        self.mx, self.my = x, y
        if self.held_card:
            self.held_card.center_x += dx
            self.held_card.center_y += dy

    def on_mouse_press(self, x, y, button, modifiers):
        # Toolbar button
        tby = SH - TOOLBAR_H // 2
        if _in_rect(x, y, SW - 130, tby - 16, SW - 20, tby + 16):
            self._go_menu()
            return

        cards_at = arcade.get_sprites_at_point((x, y), self.card_list)
        if not cards_at:
            return

        target = cards_at[-1]
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.held_card = target
            self.held_card_original_position = target.position
            if self.held_card.current_zone:
                self.held_card.current_zone.remove_card(self.held_card)
            self.card_list.remove(self.held_card)
            self.card_list.append(self.held_card)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            target.in_attack_position = not target.in_attack_position
            target.angle = 0 if target.in_attack_position else 90

    def on_mouse_release(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT or not self.held_card:
            return

        zone = self.board_manager.get_zone_at(x, y)
        if zone and not zone.is_full():
            self.held_card.position = (zone.x, zone.y)
            self.held_card.current_zone = zone
            zone.add_card(self.held_card)
        else:
            self.held_card.position = self.held_card_original_position
            if self.held_card.current_zone:
                self.held_card.current_zone.add_card(self.held_card)

        self.held_card = None

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            self._go_menu()

    def _go_menu(self):
        from menu_view import MenuView
        self.window.show_view(MenuView())

    def on_hide_view(self):
        pass
