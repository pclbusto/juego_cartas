import arcade
import arcade.gui
import constants
from card import Card
from zones import BoardManager
from database import DatabaseManager

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(constants.BG_COLOR)

        self.db = DatabaseManager()
        self.board_manager = BoardManager()
        self.card_list = arcade.SpriteList()

        # Variables para arrastrar (Drag & Drop)
        self.held_card = None
        self.held_card_original_position = None

        # UI Manager for buttons
        self.ui_manager = arcade.gui.UIManager()
        
    def setup(self):
        """ Configurar el juego, instanciar las cartas del deck de la base de datos """
        self.ui_manager.enable()
        self.card_list.clear()

        # Create UI button for returning to menu
        back_button = arcade.gui.UIFlatButton(text="Menu", width=100)
        back_button.on_click = self.on_back_to_menu

        anchor = self.ui_manager.add(arcade.gui.UIAnchorLayout())
        anchor.add(child=back_button, anchor_x="right", anchor_y="top",
                   align_x=-20, align_y=-20)

        # Obtener el primer deck disponible
        decks = self.db.get_all_decks()
        if not decks:
            print("No hay decks creados. Por favor, crea uno en el Deck Builder.")
            return

        deck_id = decks[0]['id']
        deck_cards = self.db.get_deck_cards(deck_id)

        if not deck_cards:
            print(f"El deck '{decks[0]['name']}' está vacío.")
        else:
            # Crear las cartas expandiendo las cantidades
            flat_deck = []
            for card_data in deck_cards:
                for _ in range(card_data.get('quantity', 1)):
                    flat_deck.append(card_data)

            # Limitamos a 7 cartas para la visualización inicial de prueba
            for i, card_data in enumerate(flat_deck[:7]):
                card = Card(name=card_data.get('name', '???'))
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

        # Dibujar UI
        self.ui_manager.draw()

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

    def on_back_to_menu(self, event):
        """Return to main menu."""
        from menu_view import MenuView
        menu = MenuView()
        self.window.show_view(menu)

    def on_key_press(self, symbol, modifiers):
        """Handle key presses."""
        if symbol == arcade.key.ESCAPE:
            self.on_back_to_menu(None)

    def on_hide_view(self):
        """Clean up when leaving view."""
        self.ui_manager.disable()
