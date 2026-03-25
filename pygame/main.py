import sys
import os

# Change working directory to this file's folder so that all local imports
# (menu_view, game_view, etc.) resolve to the pygame/ versions, not the
# arcade versions in the parent directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pygame
import constants

class Game:
    """Manages the window, main loop, and active view."""

    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(
            (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(constants.SCREEN_TITLE)
        self.clock        = pygame.time.Clock()
        self.current_view = None

    def show_view(self, view):
        if self.current_view:
            self.current_view.on_exit()
        self.current_view = view
        view.on_enter()

    def run(self):
        while True:
            dt = self.clock.tick(constants.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.current_view:
                    self.current_view.on_event(event)

            if self.current_view:
                self.current_view.on_update(dt)
                self.current_view.on_draw(self.screen)

            pygame.display.flip()


def main():
    game = Game()
    from menu_view import MenuView
    game.show_view(MenuView(game))
    game.run()


if __name__ == "__main__":
    main()
