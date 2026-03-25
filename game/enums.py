from enum import Enum, auto


class Position(Enum):
    ATTACK = auto()
    DEFENSE = auto()
    SET = auto()        # boca abajo (monstruo en DEF o M/T sin revelar)


class Phase(Enum):
    DRAW = auto()
    STANDBY = auto()
    MAIN1 = auto()
    BATTLE = auto()
    MAIN2 = auto()
    END = auto()


class CardType(Enum):
    MONSTER = auto()
    SPELL = auto()
    TRAP = auto()


class Attribute(Enum):
    DARK = auto()
    LIGHT = auto()
    FIRE = auto()
    WATER = auto()
    EARTH = auto()
    WIND = auto()
    DIVINE = auto()
