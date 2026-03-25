import os
from database import DatabaseManager

db = DatabaseManager()
res = db.get_setting("resolution", "1280x720")
w, h = res.split("x")

SCREEN_WIDTH = int(w)
SCREEN_HEIGHT = int(h)
SCREEN_TITLE = "Juego de Cartas Estilo YGO"

# Tamaños de carta
CARD_WIDTH = 90
CARD_HEIGHT = 130
CARD_SPACING = 110 # Distancia entre centros de cartas adyacentes

LEFT_PANEL_W = 260
RIGHT_PANEL_W = 340
BOTTOM_HAND_H = 260

# Colores
BG_COLOR = (20, 40, 60)
ZONE_COLOR = (100, 150, 200, 150)
ZONE_OUTLINE_COLOR = (255, 255, 255, 200)
TEXT_COLOR = (255, 255, 255, 255)
