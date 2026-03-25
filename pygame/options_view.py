import os
import sys
import pygame

import constants
from draw_utils import (
    BG_DEEP, PANEL_BG, SEP, TEXT, DIM, GOLD, BLUE_N,
    BTN, BTN_HOV, BTN_ACT,
    rrect_filled, rrect_outline, draw_text, draw_btn, in_rect,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)
from database import DatabaseManager

SW, SH = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT

RES_OPTIONS    = ["1280x720", "1600x900", "1920x1080", "2560x1080"]
LIMIT_OPTIONS  = [("Sin límite", None), ("2000", "2000"), ("1000", "1000"),
                  ("400",  "400"),  ("200", "200")]
FREE_OPTIONS   = [("Liberar al salir", "1"), ("Mantener en VRAM", "0")]

_SECTIONS = [
    ("Resolución",           "resolution",  RES_OPTIONS),
    ("Límite de texturas",   "thumb_limit", [v for _, v in LIMIT_OPTIONS]),
    ("GPU al salir",         "free_on_exit",[v for _, v in FREE_OPTIONS]),
]


class OptionsView:
    def __init__(self, game):
        self.game    = game
        db_path      = os.path.join(BASE_DIR, 'yugioh.db')
        self.db      = DatabaseManager(db_path)
        self.mx = self.my = 0

        self.cur = {
            "resolution":  self.db.get_setting("resolution",  "1280x720"),
            "thumb_limit": self.db.get_setting("thumb_limit", None),
            "free_on_exit":self.db.get_setting("free_on_exit","0"),
        }

    def on_enter(self): pass
    def on_exit(self):  pass

    # ── Events ───────────────────────────────────────────────────────────────

    def on_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mx, self.my = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(*event.pos)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()

    def _on_click(self, x, y):
        # Back button
        if in_rect(x, y, 8, 8, 140, 48):
            self._save()
            self._go_back()
            return

        for (label, key, opts), row_y in self._section_rows():
            for j, opt in enumerate(opts):
                bx, by, bw, bh = self._opt_btn_rect(row_y, j, len(opts))
                if in_rect(x, y, bx, by, bx + bw, by + bh):
                    self.cur[key] = opt
                    return

    # ── Geometry ─────────────────────────────────────────────────────────────

    def _section_rows(self):
        panel_w = 600
        px1     = SW // 2 - panel_w // 2
        y       = 120
        result  = []
        for sec in _SECTIONS:
            result.append((sec, y))
            y += 90
        return result

    def _opt_btn_rect(self, row_y, idx, total):
        panel_w = 600
        px1     = SW // 2 - panel_w // 2
        bw      = panel_w // max(total, 1) - 8
        bx      = px1 + idx * (bw + 8)
        by      = row_y + 30
        bh      = 34
        return bx, by, bw, bh

    # ── Draw ─────────────────────────────────────────────────────────────────

    def on_update(self, dt): pass

    def on_draw(self, surf: pygame.Surface):
        surf.fill(BG_DEEP)

        # Header
        pygame.draw.rect(surf, (20, 23, 30), pygame.Rect(0, 0, SW, 64))
        pygame.draw.line(surf, SEP, (0, 64), (SW, 64), 1)
        draw_text(surf, "Opciones", SW // 2, 32, GOLD,
                  size=20, bold=True, anchor="center")

        # Back button
        hov_back = in_rect(self.mx, self.my, 8, 8, 140, 48)
        draw_btn(surf, 74, 28, 130, 36, "← Guardar", hovered=hov_back)

        panel_w = 600
        px1     = SW // 2 - panel_w // 2

        for (label, key, opts), row_y in self._section_rows():
            # Section label
            draw_text(surf, label, px1, row_y, TEXT, size=12, bold=True)
            pygame.draw.line(surf, (*SEP, 80),
                             (px1, row_y + 18), (px1 + panel_w, row_y + 18), 1)

            # Friendly labels
            if key == "thumb_limit":
                friendly = {v: lbl for lbl, v in LIMIT_OPTIONS}
            elif key == "free_on_exit":
                friendly = {v: lbl for lbl, v in FREE_OPTIONS}
            else:
                friendly = {v: v for v in opts}

            for j, opt in enumerate(opts):
                bx, by, bw, bh = self._opt_btn_rect(row_y, j, len(opts))
                active = (self.cur[key] == opt)
                hov    = in_rect(self.mx, self.my, bx, by, bx + bw, by + bh)
                draw_btn(surf, bx + bw // 2, by + bh // 2, bw, bh,
                         friendly.get(opt, str(opt) if opt else "Sin límite"),
                         hovered=hov, active=active,
                         color=BLUE_N if active else None)

    # ── Save / nav ───────────────────────────────────────────────────────────

    def _save(self):
        for key, val in self.cur.items():
            self.db.set_setting(key, val)

    def _go_back(self):
        from menu_view import MenuView
        self.game.show_view(MenuView(self.game))
