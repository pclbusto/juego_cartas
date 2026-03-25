import pygame
import constants

CW = constants.CARD_WIDTH
CH = constants.CARD_HEIGHT

_ZONE_STYLES = {
    "Mon":   ((50, 22,  6, 130), (220, 110,  50)),
    "S/T":   (( 6, 25, 60, 130), ( 55, 135, 230)),
    "Field": ((10, 48, 16, 130), ( 70, 185,  75)),
    "GY":    ((32, 32, 32, 130), (130, 130, 130)),
    "Deck":  ((20, 20, 48, 130), ( 90,  90, 175)),
    "Extra": ((20, 20, 48, 130), ( 90,  90, 175)),
    "EMZ":   ((35, 35, 48, 130), (150, 150, 200)),
}

def _zone_style(name):
    for k, v in _ZONE_STYLES.items():
        if k in name:
            return v
    return ((35, 35, 35, 130), (100, 100, 100))

def _zone_abbr(name):
    for k in ["Deck", "Extra", "Field", "GY", "EMZ"]:
        if k in name:
            return k
    if "Mon" in name: return "MON"
    if "S/T" in name: return "S/T"
    return name.split()[-1][:3].upper()


class Zone:
    def __init__(self, name, x, y, max_capacity, owner="Player"):
        self.name         = name
        self.x            = x      # center x
        self.y            = y      # center y (pygame: y-down)
        self.max_capacity = max_capacity
        self.cards        = []
        self.owner        = owner

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - CW / 2), int(self.y - CH / 2), CW, CH)

    def add_card(self, card):
        if len(self.cards) < self.max_capacity:
            self.cards.append(card)
            return True
        return False

    def remove_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
            return True
        return False

    def is_full(self):
        return len(self.cards) >= self.max_capacity

    def check_collision(self, px, py) -> bool:
        return self.rect.collidepoint(px, py)

    def draw(self, surf: pygame.Surface):
        from draw_utils import rrect_outline, draw_text
        fill, outline_rgb = _zone_style(self.name)

        # Fill with alpha
        s = pygame.Surface((CW, CH), pygame.SRCALPHA)
        s.fill(fill)
        surf.blit(s, self.rect.topleft)

        al  = 220 if self.is_full() else 150
        lw  = 2   if self.is_full() else 1
        rx, ry = self.rect.topleft
        rrect_outline(surf, rx, ry, rx + CW, ry + CH, 4, (*outline_rgb, al), lw)

        # Zone label
        draw_text(surf, _zone_abbr(self.name),
                  self.x, self.y, (*outline_rgb, 120),
                  size=8, bold=True, anchor="center")


class BoardManager:
    def __init__(self, board_cx, board_cy, step_x, step_y):
        self.zones = []

        def add_z(name, col_off, row_off, cap, owner):
            zx = board_cx + col_off * step_x
            zy = board_cy + row_off * step_y
            self.zones.append(Zone(name, zx, zy, cap, owner))

        # In pygame y-down: row_off > 0 = lower on screen (opponent)
        #                   row_off < 0 = higher on screen (player)
        # We flip the sign vs. arcade so layout is correct:
        #   row_off = -2 → top (opponent)
        #   row_off = +2 → bottom (player)

        # ── OPPONENT (top of board) ──
        add_z("Opp Deck",  -3, -2, 60, "Opponent")
        for i in range(5):
            add_z(f"Opp S/T {5-i}", -2+i, -2, 1, "Opponent")
        add_z("Opp Extra",  3, -2, 15, "Opponent")

        add_z("Opp Field", -3, -1,  1, "Opponent")
        for i in range(5):
            add_z(f"Opp Mon {5-i}", -2+i, -1, 1, "Opponent")
        add_z("Opp GY",     3, -1, float('inf'), "Opponent")

        # ── EMZ (center) ──
        add_z("EMZ L", -1.2, 0, 1, "Shared")
        add_z("EMZ R",  1.2, 0, 1, "Shared")

        # ── PLAYER (bottom of board) ──
        add_z("Player Field", -3,  1,  1, "Player")
        for i in range(5):
            add_z(f"Player Mon {i+1}", -2+i,  1, 1, "Player")
        add_z("Player GY",     3,  1, float('inf'), "Player")

        add_z("Player Extra", -3,  2, 15, "Player")
        for i in range(5):
            add_z(f"Player S/T {i+1}", -2+i,  2, 1, "Player")
        add_z("Player Deck",   3,  2, 60, "Player")

    def get_zone_at(self, px, py):
        for zone in self.zones:
            if zone.check_collision(px, py) and not zone.is_full():
                return zone
        return None

    def draw(self, surf: pygame.Surface):
        for zone in self.zones:
            zone.draw(surf)
