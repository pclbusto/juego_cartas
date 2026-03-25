# game/player.py
#
# Player: identidad y estado en partida de un jugador.
# Las zonas y LP viven acá — el GameState los referencia.
# El GameEngine es el único que modifica estos datos.


from game.deck import Deck


class Player:
    def __init__(self, name: str, deck_id: int):
        self.name = name
        self.deck_id = deck_id
        self.selected_deck = deck_id   # el engine usa esto para cargar el mazo

        # Estado en partida (lo puebla el engine al iniciar)
        self.lp = 8000
        self.hand = []
        self.deck = Deck([])
        self.extra_deck = Deck([])
        self.graveyard = []
        self.banished = []
        self.monster_zones = [None] * 5
        self.spell_trap_zones = [None] * 5
        self.field_zone = None

    def __repr__(self):
        return f"<Player {self.name} | LP={self.lp} | deck_id={self.deck_id}>"
