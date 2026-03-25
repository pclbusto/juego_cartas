import os
import sys

# Allow importing database from the parent directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)
from database import DatabaseManager

IMAGES_DIR = os.path.join(BASE_DIR, 'images')
DB_PATH    = os.path.join(BASE_DIR, 'yugioh.db')

db = DatabaseManager(DB_PATH)
res = db.get_setting("resolution", "1280x720")
w, h = res.split("x")

SCREEN_WIDTH  = int(w)
SCREEN_HEIGHT = int(h)
SCREEN_TITLE  = "Juego de Cartas — YGO (pygame)"

CARD_WIDTH    = 90
CARD_HEIGHT   = 130
LEFT_PANEL_W  = 260
RIGHT_PANEL_W = 340
BOTTOM_HAND_H = 150
TOP_BAR_H     = 36
FPS           = 60
