# game/effect.py
#
# Effect: base de todo efecto en el juego.
# Se apila en GameState.chain cuando se activa.
# El GameEngine los resuelve en orden inverso (LIFO).
# Cada efecto concreto hereda de Effect y sobreescribe resolve().


class Effect:
    def __init__(self, source_card, controller_index: int, data: dict = None):
        # source_card: GameCard que originó el efecto
        self.source_card = source_card

        # Quién controló la activación (índice en GameState.players)
        self.controller_index = controller_index

        # Datos adicionales que necesite el efecto al resolver
        # Ejemplo: {"target": GameCard, "zone_index": 2}
        self.data = data or {}

    def resolve(self, engine):
        """Ejecuta el efecto. Recibe el GameEngine para poder operar sobre el estado."""
        raise NotImplementedError(f"{self.__class__.__name__} debe implementar resolve().")

    def __repr__(self):
        return f"<{self.__class__.__name__} | fuente: {self.source_card.name}>"
