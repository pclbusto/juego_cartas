import arcade
import constants
from card import Card
from zones import BoardManager

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(constants.BG_COLOR)
        
        self.board_manager = BoardManager()
        self.card_list = arcade.SpriteList()
        
        # Variables para arrastrar (Drag & Drop)
        self.held_card = None
        self.held_card_original_position = None
        
    def setup(self):
        """ Configurar el juego, instanciar algunas cartas de prueba """
        self.card_list.clear()
        
        # Crear 5 cartas de prueba en una "Mano" (Hand) debajo del tablero
        for i in range(5):
            card = Card(name=f"Carta {i+1}")
            card.position = (constants.CENTER_X - 250 + (125 * i), 50)
            self.card_list.append(card)

    def on_draw(self):
        """ Renderizar la pantalla """
        self.clear()

        # Dibujar Zonas (leyendo del manager en lugar de dibujarlas sueltas)
        for zone in self.board_manager.zones:
            # Calcular la esquina inferior izquierda
            left = zone.x - constants.CARD_WIDTH / 2
            bottom = zone.y - constants.CARD_HEIGHT / 2
            
            # Dibujar fondo semi-transparente
            arcade.draw_lbwh_rectangle_filled(
                left, bottom, 
                constants.CARD_WIDTH, constants.CARD_HEIGHT, 
                constants.ZONE_COLOR
            )
            
            # Dibujar borde
            arcade.draw_lbwh_rectangle_outline(
                left, bottom, 
                constants.CARD_WIDTH, constants.CARD_HEIGHT, 
                constants.ZONE_OUTLINE_COLOR, 
                2
            )
            
            # Dibujar etiqueta
            arcade.draw_text(
                zone.name.split(" ")[0], 
                zone.x, zone.y, 
                constants.TEXT_COLOR, 
                font_size=10, 
                anchor_x="center", 
                anchor_y="center"
            )
        
        # Dibujar cartas
        self.card_list.draw()

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Manejar clics. Botón izquierdo para arrastrar, derecho para cambiar modo/girar. """
        cards_at_point = arcade.get_sprites_at_point((x, y), self.card_list)
        
        if len(cards_at_point) > 0:
            # Tomamos la carta que está encima de todo
            target_card = cards_at_point[-1]
            
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.held_card = target_card
                self.held_card_original_position = target_card.position
                
                # Quitarla de su zona actual si está en alguna
                if self.held_card.current_zone:
                    self.held_card.current_zone.remove_card(self.held_card)
                    
                # Traer la carta al frente (hacerla última en la lista)
                self.card_list.remove(self.held_card)
                self.card_list.append(self.held_card)
                
            elif button == arcade.MOUSE_BUTTON_RIGHT:
                # Cambiar posición (ataque/defensa)
                if target_card.in_attack_position:
                    target_card.in_attack_position = False
                    target_card.angle = 90
                else:
                    target_card.in_attack_position = True
                    target_card.angle = 0

    def on_mouse_motion(self, x, y, dx, dy):
        """ Arrastrar la carta """
        if self.held_card:
            self.held_card.center_x += dx
            self.held_card.center_y += dy

    def on_mouse_release(self, x, y, button, key_modifiers):
        """ Soltar la carta """
        if button == arcade.MOUSE_BUTTON_LEFT and self.held_card:
            # Buscar si soltamos en una zona
            zone = self.board_manager.get_zone_at(x, y)
            
            if zone and not zone.is_full():
                # Colocar en la zona
                self.held_card.position = (zone.x, zone.y)
                self.held_card.current_zone = zone
                zone.add_card(self.held_card)
                
                # Reglas especiales por zona
                if "GY" in zone.name or "Deck" in zone.name or "Extra" in zone.name:
                    # En GY, tal vez poner boca arriba. En Deck, boca abajo
                    # Esto es solo estética básica
                    pass
            else:
                # Retornar a la posición original
                self.held_card.position = self.held_card_original_position
                if self.held_card.current_zone:
                    # Volver a asignarla a la zona de la que vino
                    self.held_card.current_zone.add_card(self.held_card)
                    
            self.held_card = None
