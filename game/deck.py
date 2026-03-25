# game/deck.py
#
# Deck: contenedor del mazo de un jugador.
# Encapsula el acceso y manipulación de las cartas.
# El GameEngine lo usa para robar, mezclar y buscar — nunca accede a la lista directamente.

import random
from game.game_card import GameCard


class Deck:
    def __init__(self, cards: list[GameCard]):
        self._cards = cards  # índice 0 = tope del mazo

    def draw(self) -> GameCard:
        """Saca y devuelve la carta del tope. Lanza excepción si está vacío."""
        if not self._cards:
            raise IndexError("El mazo está vacío.")
        return self._cards.pop(0)

    def peek(self) -> GameCard:
        """Devuelve la carta del tope sin sacarla."""
        if not self._cards:
            raise IndexError("El mazo está vacío.")
        return self._cards[0]

    def shuffle(self):
        """Mezcla el mazo."""
        random.shuffle(self._cards)

    def add_top(self, card: GameCard):
        """Agrega una carta al tope del mazo."""
        self._cards.insert(0, card)

    def add_bottom(self, card: GameCard):
        """Agrega una carta al fondo del mazo."""
        self._cards.append(card)

    def search(self, name: str) -> GameCard | None:
        """Busca una carta por nombre exacto. Devuelve la primera coincidencia o None."""
        for card in self._cards:
            if card.name == name:
                return card
        return None

    def remove(self, card: GameCard):
        """Saca una carta específica del mazo (para efectos de búsqueda)."""
        self._cards.remove(card)

    def is_empty(self) -> bool:
        return len(self._cards) == 0

    def __len__(self) -> int:
        return len(self._cards)

    def __repr__(self) -> str:
        return f"<Deck {len(self._cards)} cartas>"
