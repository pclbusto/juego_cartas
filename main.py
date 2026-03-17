import arcade
from menu_view import MenuView
import constants

def main():
    window = arcade.Window(
        constants.SCREEN_WIDTH,
        constants.SCREEN_HEIGHT,
        constants.SCREEN_TITLE
    )

    # Iniciar con el menú principal
    menu_view = MenuView()
    window.show_view(menu_view)

    arcade.run()

if __name__ == "__main__":
    main()
