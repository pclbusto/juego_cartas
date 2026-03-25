# game/effects/ — registro de efectos implementados
#
# Para agregar un efecto nuevo:
#   1. Creá su archivo acá (ej: dark_hole.py)
#   2. Registralo en EFFECT_REGISTRY con su key

EFFECT_REGISTRY: dict = {}

# Ejemplo de cómo se registran (descomentar cuando implementes):
# from game.effects.dark_hole import DestroyAllMonsters
# EFFECT_REGISTRY["destroy_all_monsters"] = DestroyAllMonsters
