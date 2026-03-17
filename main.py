import arcade
from game_view import GameView
import constants

def main():
    window = arcade.Window(
        constants.SCREEN_WIDTH, 
        constants.SCREEN_HEIGHT, 
        constants.SCREEN_TITLE
    )
    
    # Iniciar la vista del juego
    game_view = GameView()
    game_view.setup()
    window.show_view(game_view)
    
    arcade.run()

if __name__ == "__main__":
    main()
