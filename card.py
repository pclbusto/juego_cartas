import arcade
import constants

class Card(arcade.SpriteSolidColor):
    """ Carta básica genérica """

    def __init__(self, name="Carta Básica", card_type="Monster"):
        super().__init__(constants.CARD_WIDTH, constants.CARD_HEIGHT, arcade.color.WHEAT)
        self.name = name
        self.card_type = card_type
        
        # Estados
        self.face_up = True
        self.in_attack_position = True
        
        # Zona actual
        self.current_zone = None

    def draw(self, **kwargs):
        """ Sobrescribimos el draw para añadir texto temporal """
        super().draw(**kwargs)
        
        if self.face_up:
             # Mostramos el nombre si está boca arriba
             arcade.draw_text(
                 self.name, 
                 self.center_x, self.center_y, 
                 arcade.color.BLACK, 
                 font_size=10, 
                 anchor_x="center", 
                 anchor_y="center"
             )
        else:
             # Un color diferente para el dorso y texto
             left = self.center_x - constants.CARD_WIDTH / 2
             bottom = self.center_y - constants.CARD_HEIGHT / 2
             arcade.draw_lbwh_rectangle_filled(
                 left, bottom, 
                 constants.CARD_WIDTH, constants.CARD_HEIGHT, 
                 arcade.color.MAROON
             )
             arcade.draw_text(
                 "Dorso", 
                 self.center_x, self.center_y, 
                 arcade.color.WHITE, 
                 font_size=12, 
                 anchor_x="center", 
                 anchor_y="center"
             )
