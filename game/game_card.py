# game/game_card.py
#
# GameCard: instancia de una carta en juego.
# Wrappea los datos estáticos de la DB y agrega estado dinámico.
# No tiene lógica de reglas — solo datos mutables de una carta en partida.


from game.enums import Position, CardType, Attribute


class GameCard:
    def __init__(self, card_data: dict):
        # Datos estáticos (del to_dict() de la DB, no cambian)
        self.data = card_data

        # Conversión de strings de DB a enums — única frontera de parseo
        self.card_type = CardType[card_data['card_type']]
        self.attribute = self._parse_attribute(card_data.get('attribute', ''))

        # Keys de efectos implementados para esta carta
        self.effect_keys: list[str] = card_data.get('effects', [])

        # Estado dinámico (cambia durante la partida)
        self.face_up = True
        self.position = Position.ATTACK
        self.zone = None            # referencia a la Zone donde está
        self.counters = {}          # {"veneno": 2, "hielo": 1, ...}
        self.is_negated = False     # efecto negado (ej: Skill Drain)
        self.attacked_this_turn = False
        self.summoned_this_turn = False
        self.set_on_turn: int | None = None  # turno en que fue colocada boca abajo

    @staticmethod
    def _parse_attribute(raw: str):
        try:
            return Attribute[raw.upper()]
        except KeyError:
            return None  # Spell/Trap no tienen atributo

    # Accesos rápidos a los datos estáticos
    @property
    def name(self):
        return self.data.get('name', '?')

    @property
    def atk(self):
        return self.data.get('atk', 0)

    @property
    def def_(self):
        return self.data.get('def', 0)

    @property
    def level(self):
        return self.data.get('level')

    @property
    def subtype(self):
        return self.data.get('type', '')

    def __repr__(self):
        return f"<GameCard {self.name} | {self.position} | face_up={self.face_up}>"
