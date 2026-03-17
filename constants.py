SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Juego de Cartas Estilo YGO"

# Tamaños de carta
CARD_WIDTH = 90
CARD_HEIGHT = 130
CARD_SPACING = 110 # Distancia entre centros de cartas adyacentes

# Posiciones base para el jugador (mitad inferior de la pantalla)
PLAYER_Y_OFFSET = 50

# Y para la fila de Monstruos
MONSTER_ZONE_Y = 300 + PLAYER_Y_OFFSET
# Y para la fila de Magias y Trampas
SPELL_TRAP_ZONE_Y = 150 + PLAYER_Y_OFFSET

# Centros X de las 5 zonas principales
CENTER_X = SCREEN_WIDTH // 2
ZONE_X_POSITIONS = [
    CENTER_X - CARD_SPACING * 2,
    CENTER_X - CARD_SPACING,
    CENTER_X,
    CENTER_X + CARD_SPACING,
    CENTER_X + CARD_SPACING * 2,
]

# Zonas laterales
FIELD_ZONE_X = 200
FIELD_ZONE_Y = MONSTER_ZONE_Y

GRAVEYARD_X = 1080
GRAVEYARD_Y = MONSTER_ZONE_Y

EXTRA_DECK_X = 200
EXTRA_DECK_Y = SPELL_TRAP_ZONE_Y

DECK_X = 1080
DECK_Y = SPELL_TRAP_ZONE_Y

# Zonas de Péndulo (entre las zonas principales y las laterales)
PENDULUM_LEFT_X = 310
PENDULUM_RIGHT_X = 970
PENDULUM_Y = 225 + PLAYER_Y_OFFSET

# Colores
BG_COLOR = (20, 40, 60)
ZONE_COLOR = (100, 150, 200, 150)
ZONE_OUTLINE_COLOR = (255, 255, 255, 200)
TEXT_COLOR = (255, 255, 255, 255)
