import arcade
import constants

class Zone:
    def __init__(self, name, x, y, max_capacity, owner="Player"):
        self.name = name
        self.x = x
        self.y = y
        self.max_capacity = max_capacity
        self.cards = []  # Lista de cartas actualmente en esta zona
        self.owner = owner

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

    def check_collision(self, x, y):
        """ Retorna True si las coordenadas están dentro de la zona """
        # Colisión caja delimitadora
        left = self.x - constants.CARD_WIDTH / 2
        right = self.x + constants.CARD_WIDTH / 2
        bottom = self.y - constants.CARD_HEIGHT / 2
        top = self.y + constants.CARD_HEIGHT / 2
        
        return left <= x <= right and bottom <= y <= top

class BoardManager:
    """ Gestiona todas las zonas del campo """
    def __init__(self, board_cx, board_cy, step_x, step_y):
        self.zones = []
        
        def add_z(name, col_off, row_off, cap, owner):
            # col_off from -3 to +3
            # row_off from -2 to +2
            zx = board_cx + col_off * step_x
            zy = board_cy + row_off * step_y
            self.zones.append(Zone(name, zx, zy, cap, owner))

        # ── OPPONENT (Top) ──
        # S/T + Deck/Extra
        add_z("Opp Deck", -3, 2, 60, "Opponent")
        for i in range(5):
            add_z(f"Opp S/T {5-i}", -2+i, 2, 1, "Opponent")
        add_z("Opp Extra", 3, 2, 15, "Opponent")
        
        # Monsters + Field/GY
        add_z("Opp Field", -3, 1, 1, "Opponent")
        for i in range(5):
            add_z(f"Opp Mon {5-i}", -2+i, 1, 1, "Opponent")
        add_z("Opp GY", 3, 1, float('inf'), "Opponent")

        # ── EMZ (Center) ──
        add_z("EMZ L", -1.2, 0, 1, "Shared")
        add_z("EMZ R",  1.2, 0, 1, "Shared")

        # ── PLAYER (Bottom) ──
        # Monsters + Field/GY
        add_z("Player Field", -3, -1, 1, "Player")
        for i in range(5):
            add_z(f"Player Mon {i+1}", -2+i, -1, 1, "Player")
        add_z("Player GY", 3, -1, float('inf'), "Player")

        # S/T + Deck/Extra
        add_z("Player Extra", -3, -2, 15, "Player")
        for i in range(5):
            add_z(f"Player S/T {i+1}", -2+i, -2, 1, "Player")
        add_z("Player Deck", 3, -2, 60, "Player")

    def get_zone_at(self, x, y):
        """ Retorna la zona debajo del ratón si no está llena """
        for zone in self.zones:
            if zone.check_collision(x, y):
                return zone
        return None
