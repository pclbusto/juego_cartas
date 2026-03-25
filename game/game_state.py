# game/game_state.py
#
# GameState: foto completa del juego en un momento dado.
# Solo almacena datos — no aplica reglas, no valida nada.
# El GameEngine es el único que tiene permiso de modificarlo.

from game.enums import Phase
from game.player import Player


class GameState:
    def __init__(self, player1: Player, player2: Player):
        self.players = [player1, player2]

        # Control de turno
        self.turn_number = 1
        self.active_player_index = 0
        self.phase = Phase.DRAW

        # Zona de campo compartida (Extra Monster Zones)
        self.emz = [None, None]

        # Estado de la cadena en curso
        self.chain = []                    # lista de Effect apilados (LIFO)
        self.chain_open = False            # True = esperando que alguien responda

        # Ventana de prioridad
        self.priority_window_open = False
        self.priority_holder = 0           # índice del jugador que tiene la prioridad
        self.consecutive_passes = 0        # se cierra la ventana cuando llega a 2

        # Flags de turno
        self.normal_summon_used = False
        self.battle_phase_available = True

        # Input pendiente: descripción de lo que necesita el motor del jugador.
        # None = el motor no está esperando nada.
        # Ejemplo: {"type": "select_tribute", "count": 2, "valid_zones": [0, 1, 3]}
        self.pending_input: dict | None = None

    @property
    def active_player(self) -> Player:
        return self.players[self.active_player_index]

    @property
    def inactive_player(self) -> Player:
        return self.players[1 - self.active_player_index]

    def mostrar(self):
        """Imprime el estado completo del tablero en consola."""
        sep = "─" * 60
        print(sep)
        print(f" Turno {self.turn_number} | Fase: {self.phase.name} | Jugador activo: {self.active_player.name}")
        print(sep)
        for player in reversed(self.players):  # oponente arriba, jugador activo abajo
            marker = "▶" if player is self.active_player else " "
            print(f"{marker} {player.name}  LP: {player.lp}  |  Deck: {len(player.deck)}  |  Mano: {len(player.hand)}  |  Cementerio: {len(player.graveyard)}")
            print(f"  Monstruos : {self._mostrar_zonas(player.monster_zones)}")
            print(f"  Magias/Tr : {self._mostrar_zonas(player.spell_trap_zones)}")
            print(f"  Mano      : {[c.name for c in player.hand]}")
            print()
        if self.chain:
            print(f"  Cadena activa: {[str(e) for e in self.chain]}")
        print(sep)

    @staticmethod
    def _mostrar_zonas(zones: list) -> str:
        partes = []
        for i, card in enumerate(zones):
            if card is None:
                partes.append(f"[{i}] ---")
            elif card.face_up:
                partes.append(f"[{i}] {card.name} {card.position.name}")
            else:
                partes.append(f"[{i}] ???")
        return "  ".join(partes)
