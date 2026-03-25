import pygame
from draw_utils import (BG_DEEP, PANEL_BG, SEP, TEXT, DIM, GOLD, BLUE_N,
                         rrect_filled, rrect_outline, draw_text, draw_btn, in_rect)
import constants

SW, SH = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT

_BUTTONS = [
    ("deck_builder", "Deck Builder"),
    ("play",         "Jugar"),
    ("options",      "Opciones"),
    ("quit",         "Salir"),
]

BTN_W, BTN_H, BTN_GAP = 280, 46, 14


class MenuView:
    def __init__(self, game):
        self.game = game
        self.mx = self.my = 0

    def _btn_rects(self):
        total_h = len(_BUTTONS) * BTN_H + (len(_BUTTONS) - 1) * BTN_GAP
        start_y = SH // 2 - total_h // 2
        cx = SW // 2
        result = []
        for i, (action, label) in enumerate(_BUTTONS):
            cy = start_y + i * (BTN_H + BTN_GAP) + BTN_H // 2
            result.append((action, label, cx, cy))
        return result

    def on_enter(self): pass
    def on_exit(self):  pass

    def on_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mx, self.my = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for action, label, cx, cy in self._btn_rects():
                x1, y1 = cx - BTN_W // 2, cy - BTN_H // 2
                if in_rect(self.mx, self.my, x1, y1, x1 + BTN_W, y1 + BTN_H):
                    self._dispatch(action)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def on_update(self, dt): pass

    def on_draw(self, surf: pygame.Surface):
        surf.fill(BG_DEEP)

        # Top bar
        pygame.draw.rect(surf, PANEL_BG, pygame.Rect(0, 0, SW, 60))
        pygame.draw.line(surf, SEP, (0, 60), (SW, 60), 1)
        draw_text(surf, "YU-GI-OH  ·  Card Game",
                  SW // 2, 30, GOLD, size=22, bold=True, anchor="center")

        # Bottom bar
        pygame.draw.rect(surf, PANEL_BG, pygame.Rect(0, SH - 30, SW, 30))
        pygame.draw.line(surf, SEP, (0, SH - 30), (SW, SH - 30), 1)
        draw_text(surf, "v1.0 — Deck Builder Edition",
                  SW // 2, SH - 15, DIM, size=10, anchor="center")

        # Decorative line
        lx1, lx2 = SW // 2 - 160, SW // 2 + 160
        pygame.draw.line(surf, (*SEP, 80), (lx1, SH // 2 - 160), (lx2, SH // 2 - 160))

        # Buttons
        for action, label, cx, cy in self._btn_rects():
            x1, y1 = cx - BTN_W // 2, cy - BTN_H // 2
            hov = in_rect(self.mx, self.my, x1, y1, x1 + BTN_W, y1 + BTN_H)
            draw_btn(surf, cx, cy, BTN_W, BTN_H, label, hovered=hov)

    def _dispatch(self, action):
        if action == "deck_builder":
            from deck_builder_view import DeckBuilderView
            self.game.show_view(DeckBuilderView(self.game))
        elif action == "play":
            from game_view import GameView
            v = GameView(self.game)
            v.setup()
            self.game.show_view(v)
        elif action == "options":
            from options_view import OptionsView
            self.game.show_view(OptionsView(self.game))
        elif action == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
