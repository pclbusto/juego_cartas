import arcade
import constants

class Zone:
    def __init__(self, name, x, y, max_capacity):
        self.name = name
        self.x = x
        self.y = y
        self.max_capacity = max_capacity
        self.cards = []  # Lista de cartas actualmente en esta zona

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
    """ Gestiona todas las zonas de un jugador """
    def __init__(self):
        self.zones = []
        
        # Instanciar zonas de monstruos
        for i, x in enumerate(constants.ZONE_X_POSITIONS):
            self.zones.append(Zone(f"Monster {i+1}", x, constants.MONSTER_ZONE_Y, 1))
            
        # Instanciar zonas de magia/trampa
        for i, x in enumerate(constants.ZONE_X_POSITIONS):
            self.zones.append(Zone(f"Spell/Trap {i+1}", x, constants.SPELL_TRAP_ZONE_Y, 1))
            
        # Instanciar zonas de péndulo
        self.zones.append(Zone("Pendulum Left", constants.PENDULUM_LEFT_X, constants.PENDULUM_Y, 1))
        self.zones.append(Zone("Pendulum Right", constants.PENDULUM_RIGHT_X, constants.PENDULUM_Y, 1))
        
        # Instanciar Zonas Laterales
        self.zones.append(Zone("Field", constants.FIELD_ZONE_X, constants.FIELD_ZONE_Y, 1))
        self.zones.append(Zone("Extra Deck", constants.EXTRA_DECK_X, constants.EXTRA_DECK_Y, float('inf')))
        self.zones.append(Zone("GY", constants.GRAVEYARD_X, constants.GRAVEYARD_Y, float('inf')))
        self.zones.append(Zone("Deck", constants.DECK_X, constants.DECK_Y, 60)) # Limite de deck
        
    def get_zone_at(self, x, y):
        """ Retorna la zona debajo del ratón si no está llena """
        for zone in self.zones:
            if zone.check_collision(x, y):
                return zone
        return None
