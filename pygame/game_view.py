import os
import sys
import pygame
import PIL.Image

import constants
from card import Card, load_full
from zones import BoardManager
from draw_utils import (
    BG_DEEP, BOARD_BG, PANEL_BG, SEP, TEXT, DIM, GOLD, BLUE_N, RED_N,
    BTN, BTN_HOV, BTN_ACT, C_MONSTER, C_SPELL, C_TRAP, ATTR_COLORS, TYPE_COLOR,
    rrect_filled, rrect_outline, fill_rect_alpha, draw_line_alpha,
    draw_text, draw_text_wrap, draw_neon_text, draw_btn, in_rect,
    neon_lp, draw_circle_alpha, get_font,
)

SW  = constants.SCREEN_WIDTH
SH  = constants.SCREEN_HEIGHT
CW  = constants.CARD_WIDTH
CH  = constants.CARD_HEIGHT
LW  = constants.LEFT_PANEL_W
RW  = constants.RIGHT_PANEL_W
HH  = constants.BOTTOM_HAND_H
TH  = constants.TOP_BAR_H

# Board pixel bounds (pygame y-down)
BX1 = LW
BX2 = SW - RW
BY1 = TH
BY2 = SH - HH

_PHASES       = ["DP", "SP", "M1", "BP", "M2", "EP"]
_PHASE_LABELS = {
    "DP": "Robo", "SP": "Reserva", "M1": "Principal 1",
    "BP": "Batalla", "M2": "Principal 2", "EP": "Fin",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)
from database import DatabaseManager


class GameView:
    def __init__(self, game):
        self.game = game
        db_path   = os.path.join(BASE_DIR, 'yugioh.db')
        self.db   = DatabaseManager(db_path)

        self.card_list:  list[Card] = []
        self.held_card:  Card | None = None
        self.hover_card: Card | None = None
        self.held_orig:  tuple | None = None
        self.selected_field_card: Card | None = None
        self.deck_name = ""
        self.mx = self.my = 0

        # Deck selector
        self._selecting = True
        self._all_decks = []

        # Duel state
        self.player_lp     = 8000
        self.opponent_lp   = 4000
        self.player_hand   = 0
        self.opponent_hand = 5
        self.player_gy     = 0
        self.opponent_gy   = 0
        self.current_phase = "M1"
        self.duel_log: list[tuple[str, tuple]] = [("Duelo iniciado", DIM)]

        # Board
        bw = BX2 - BX1
        bh = BY2 - BY1
        board_cx = BX1 + bw / 2
        board_cy = BY1 + bh / 2
        step_x   = min(bw / 8,  CW + 16)
        step_y   = min(bh / 5.5, CH + 14)
        self.board = BoardManager(board_cx, board_cy, step_x, step_y)

        # Full-size detail texture cache
        self._detail_cache: dict[str, pygame.Surface | None] = {}

    def setup(self):
        self._all_decks = self.db.get_all_decks()
        self._selecting = True

    # ── Deck loader ──────────────────────────────────────────────────────────

    def _load_deck(self, deck: dict):
        self.card_list.clear()
        self.deck_name = deck['name']
        flat = []
        for cd in self.db.get_deck_cards(deck['id']):
            for _ in range(cd.get('quantity', 1)):
                flat.append(cd)

        n   = min(5, len(flat))
        bw  = BX2 - BX1
        gap = min(CW + 10, (bw - 40) / max(n, 1))
        cx0 = BX1 + bw / 2 - gap * (n - 1) / 2
        card_y = BY2 + HH // 2   # center of hand area

        for i, cd in enumerate(flat[:5]):
            c   = Card(card_data=cd)
            c.x = cx0 + gap * i
            c.y = card_y
            self.card_list.append(c)

        self.player_hand = len(self.card_list)
        self._log(f"Deck cargado: {self.deck_name}", BLUE_N)
        self._log(f"Jugador robó {self.player_hand} cartas", BLUE_N)
        self._selecting = False

    # ── Detail texture ───────────────────────────────────────────────────────

    def _get_detail(self, image_name: str, tw: int, th: int) -> pygame.Surface | None:
        key = (image_name, tw, th)
        if key not in self._detail_cache:
            self._detail_cache[key] = load_full(image_name, tw, th)
        return self._detail_cache[key]

    # ── Events ───────────────────────────────────────────────────────────────

    def on_enter(self): pass
    def on_exit(self):  pass

    def on_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mx, self.my = event.pos
            if self.held_card:
                dx = event.rel[0]
                dy = event.rel[1]
                self.held_card.x += dx
                self.held_card.y += dy
            else:
                hits = [c for c in self.card_list if c.collides_with_point(*event.pos)]
                self.hover_card = hits[-1] if hits else None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self._selecting:
                self._handle_sel_click(*event.pos)
                return
            if event.button == 1:
                self._on_lclick(*event.pos)
            elif event.button == 3:
                self._on_rclick(*event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._on_release(*event.pos)

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_menu()

    def _on_lclick(self, x, y):
        # Menu button
        if in_rect(x, y, 12, TH + 8, LW - 12, TH + 42):
            self._go_menu()
            return
        # Pick up card
        hits = [c for c in self.card_list if c.collides_with_point(x, y)]
        if hits:
            self.held_card = hits[-1]
            self.held_orig = (self.held_card.x, self.held_card.y)
            if self.held_card.current_zone:
                self.held_card.current_zone.remove_card(self.held_card)
            # move to top of draw order
            self.card_list.remove(self.held_card)
            self.card_list.append(self.held_card)

    def _on_rclick(self, x, y):
        hits = [c for c in self.card_list if c.collides_with_point(x, y)]
        if hits:
            t = hits[-1]
            t.in_attack = not t.in_attack

    def _on_release(self, x, y):
        if not self.held_card:
            return
        zone = self.board.get_zone_at(x, y)
        if zone and not zone.is_full():
            self.held_card.x = zone.x
            self.held_card.y = zone.y
            self.held_card.current_zone = zone
            zone.add_card(self.held_card)
            self._log(f"Jugador colocó {self.held_card.name} en {zone.name}", BLUE_N)
        else:
            if self.held_orig:
                self.held_card.x, self.held_card.y = self.held_orig
            if self.held_card.current_zone:
                self.held_card.current_zone.add_card(self.held_card)
        self.held_card = None
        self.held_orig  = None

    def on_update(self, dt): pass

    # ── Draw ─────────────────────────────────────────────────────────────────

    def on_draw(self, surf: pygame.Surface):
        if self._selecting:
            self._draw_deck_selector(surf)
            return

        surf.fill(BG_DEEP)

        # Board area
        pygame.draw.rect(surf, BOARD_BG, pygame.Rect(BX1, BY1, BX2 - BX1, BY2 - BY1))

        # Glass container
        rrect_outline(surf, BX1 + 12, BY1 + 12, BX2 - 12, BY2 - 12, 10,
                      (*SEP, 170), 1)

        # Center line
        mid_y = (BY1 + BY2) // 2
        draw_line_alpha(surf, BX1 + 12, mid_y, BX2 - 12, mid_y, (*SEP, 110), 1)

        # Zones
        self.board.draw(surf)

        # Selected field card glow
        if self.selected_field_card:
            fc = self.selected_field_card
            r  = max(CW, CH) // 2 + 6
            for dr, al in [(r + 12, 12), (r + 8, 30), (r + 4, 65), (r + 1, 120)]:
                draw_circle_alpha(surf, fc.x, fc.y, dr, (*BLUE_N, al), 2)
            draw_circle_alpha(surf, fc.x, fc.y, r, (*BLUE_N, 240), 2)

        # Hand container
        hw  = min(BX2 - BX1 - 20, 700)
        hx1 = BX1 + (BX2 - BX1) // 2 - hw // 2
        hx2 = hx1 + hw
        hy1 = BY2 + 4
        hy2 = SH - 4
        rrect_filled (surf, hx1, hy1, hx2, hy2, 10, (14, 17, 24, 235))
        rrect_outline(surf, hx1, hy1, hx2, hy2, 10, (*SEP, 130), 1)

        # "Hand" vertical label on left side
        hand_font = get_font(9, bold=True)
        hand_surf = hand_font.render("MANO", True, DIM)
        hand_surf.set_alpha(130)
        hand_rot  = pygame.transform.rotate(hand_surf, 90)
        surf.blit(hand_rot, (hx1 + 6, hy1 + (hy2 - hy1) // 2 - hand_rot.get_height() // 2))

        # Tooltip at bottom of hand container
        draw_text(surf, "Click Izq: Seleccionar  ·  Click Der: Acción  ·  Rueda: Zoom",
                  (hx1 + hx2) // 2, hy2 - 8, (*DIM, 120), size=8, anchor="midbottom")

        # Cards
        for card in self.card_list:
            card.draw(surf)

        # Held card glow
        if self.held_card:
            hc = self.held_card
            rx, ry = int(hc.x - CW / 2), int(hc.y - CH / 2)
            for exp, al in [(8, 25), (5, 60), (2, 130)]:
                rrect_outline(surf, rx - exp, ry - exp,
                              rx + CW + exp, ry + CH + exp,
                              6, (*GOLD, al), 1)

        # Hover card glow
        if self.hover_card and not self.held_card:
            hc = self.hover_card
            rx, ry = int(hc.x - CW / 2), int(hc.y - CH / 2)
            for exp, al in [(6, 18), (3, 55)]:
                rrect_outline(surf, rx - exp, ry - exp,
                              rx + CW + exp, ry + CH + exp,
                              6, (*BLUE_N, al), 1)

        self._draw_left_panel(surf)
        self._draw_right_panel(surf)
        self._draw_top_bar(surf)

    # ── Top bar ──────────────────────────────────────────────────────────────

    def _draw_top_bar(self, surf: pygame.Surface):
        pygame.draw.rect(surf, (20, 23, 30), pygame.Rect(0, 0, SW, TH))
        pygame.draw.line(surf, SEP, (0, TH), (SW, TH), 1)

        draw_text(surf, "Tablero de Duelo  YGO",
                  LW + 14, TH // 2, DIM, size=11, anchor="midleft")

        # Filter toggles
        filters = [("Monstruos", C_MONSTER), ("Hechizos", C_SPELL), ("Trampa", C_TRAP)]
        fw, fh, fg = 90, 22, 8
        total = len(filters) * fw + (len(filters) - 1) * fg
        fx = SW // 2 - total // 2
        fy = TH // 2
        for label, col in filters:
            hov = in_rect(self.mx, self.my, fx, fy - fh // 2, fx + fw, fy + fh // 2)
            fill_rect_alpha(surf, fx, fy - fh // 2, fx + fw, fy + fh // 2,
                            (*col, 40 if hov else 18))
            pygame.draw.rect(surf, (*col, 100 if hov else 55),
                             pygame.Rect(fx, fy - fh // 2, fw, fh), 1)
            draw_text(surf, label, fx + fw // 2, fy, (*col, 220),
                      size=9, anchor="center")
            fx += fw + fg

        # Deck name
        if self.deck_name:
            draw_text(surf, self.deck_name, SW - RW - 12, TH // 2,
                      (*GOLD, 180), size=10, italic=True, anchor="midright")

    # ── Left panel ───────────────────────────────────────────────────────────

    def _draw_left_panel(self, surf: pygame.Surface):
        cx = LW // 2

        pygame.draw.rect(surf, PANEL_BG, pygame.Rect(0, 0, LW, SH))
        pygame.draw.line(surf, SEP, (LW, 0), (LW, SH), 1)

        # ── Menu button ─────────────────────────────────────────────────────
        hov_menu = in_rect(self.mx, self.my, 12, TH + 6, LW - 12, TH + 38)
        draw_btn(surf, cx, TH + 22, LW - 24, 30, "Pausar / Menú", hovered=hov_menu)
        _hsep(surf, TH + 44)

        y = TH + 52

        # ── Opponent block ───────────────────────────────────────────────────
        av_h = 70
        _av_box(surf, cx, y, y + av_h, RED_N, "?")
        y += av_h + 4
        neon_lp(surf, cx, y + 18, self.opponent_lp, RED_N)
        y += 38
        draw_text(surf, f"Mano: {self.opponent_hand}   Cementerio: {self.opponent_gy}",
                  cx, y, (*RED_N, 160), size=9, anchor="midtop")
        y += 18
        _hsep(surf, y)
        y += 6

        # ── Phase strip ─────────────────────────────────────────────────────
        y = _draw_phases(surf, y, self.current_phase)
        _hsep(surf, y)
        y += 6

        # ── Player block ─────────────────────────────────────────────────────
        _av_box(surf, cx, y, y + av_h, BLUE_N, "J")
        y += av_h + 4
        neon_lp(surf, cx, y + 18, self.player_lp, BLUE_N)
        y += 38
        draw_text(surf, f"Mano: {self.player_hand}   Cementerio: {self.player_gy}",
                  cx, y, (*BLUE_N, 160), size=9, anchor="midtop")
        y += 18
        _hsep(surf, y)
        y += 6

        # ── Action buttons (fill remaining space) ────────────────────────────
        rem = SH - y
        mid = y + rem // 2
        hov_bat = in_rect(self.mx, self.my, 12, mid - 48, LW - 12, mid - 6)
        hov_pas = in_rect(self.mx, self.my, 12, mid + 6,  LW - 12, mid + 48)
        draw_btn(surf, cx, mid - 27, LW - 24, 36, "Fase de Batalla",
                 hovered=hov_bat, active=True, color=BTN_ACT)
        draw_btn(surf, cx, mid + 27, LW - 24, 36, "Pasar Turno",
                 hovered=hov_pas, color=GOLD)

    # ── Right panel ──────────────────────────────────────────────────────────

    def _draw_right_panel(self, surf: pygame.Surface):
        rx  = SW - RW
        cx  = rx + RW // 2

        pygame.draw.rect(surf, PANEL_BG, pygame.Rect(rx, 0, RW, SH))
        pygame.draw.line(surf, SEP, (rx, 0), (rx, SH), 1)

        # Header
        hdr_y = TH + 18
        draw_text(surf, "Detalles de Carta", cx, hdr_y, TEXT,
                  size=12, bold=True, anchor="center")
        pygame.draw.line(surf, (*SEP, 90), (rx + 10, hdr_y + 14), (SW - 10, hdr_y + 14), 1)

        cdata = self.hover_card.card_data if self.hover_card else None

        if cdata:
            ctype = cdata.get('card_type', 'MONSTER')
            attr  = cdata.get('attribute', '')
            tc    = TYPE_COLOR.get(ctype, DIM)

            # Card image
            img_area_y = hdr_y + 20
            img_area_h = 200
            ix1, ix2 = rx + 14, SW - 14
            iy1, iy2 = img_area_y, img_area_y + img_area_h

            img_name  = cdata.get('image_name', '')
            detail    = self._get_detail(img_name, ix2 - ix1, iy2 - iy1) if img_name else None

            if detail:
                dw, dh = detail.get_size()
                dcx = (ix1 + ix2) // 2
                dcy = (iy1 + iy2) // 2
                dest = pygame.Rect(dcx - dw // 2, dcy - dh // 2, dw, dh)
                # glow
                for exp, al in [(5, 18), (3, 50), (1, 100)]:
                    fill_rect_alpha(surf, dest.x - exp, dest.y - exp,
                                    dest.right + exp, dest.bottom + exp, (*tc, al))
                surf.blit(detail, dest.topleft)
            else:
                fill_rect_alpha(surf, ix1, iy1, ix2, iy2, (28, 30, 40, 255))
                rrect_outline(surf, ix1, iy1, ix2, iy2, 8, (*tc, 180), 1)
                draw_text(surf, ctype, cx, (iy1 + iy2) // 2, (*tc, 70),
                          size=22, bold=True, anchor="center")

            # Name
            ny = iy2 + 12
            draw_text(surf, cdata.get('name', '?'), rx + 12, ny, TEXT,
                      size=12, bold=True, anchor="midleft")

            # Subtype badge
            badge_lbl = cdata.get('type') or ctype
            draw_text(surf, badge_lbl[:20], SW - 12, ny, (*tc, 190),
                      size=9, italic=True, anchor="midright")

            pygame.draw.line(surf, (*SEP, 55), (rx + 10, ny + 14), (SW - 10, ny + 14), 1)

            # Stat grid
            grid_y  = ny + 20
            cell_w  = (RW - 24) // 2 - 2
            pad_x   = rx + 10

            if ctype == 'MONSTER':
                lvl      = cdata.get('level') or 0
                attr_col = ATTR_COLORS.get(attr, DIM)

                # Row 1: Tipo | Atributo
                _stat_cell(surf, pad_x, grid_y, cell_w, "◈", tc, "TIPO", ctype, tc)
                _stat_cell(surf, pad_x + cell_w + 4, grid_y, cell_w,
                           "●", attr_col, "ATR", attr or '-', attr_col)

                # Row 2: Nivel | ATK | DEF
                row2_y  = grid_y + 32
                narrow  = (RW - 28) // 3

                _stat_cell(surf, pad_x, row2_y, narrow,
                           "★", GOLD, "NVL", str(int(lvl)), GOLD)
                _stat_cell(surf, pad_x + narrow + 3, row2_y, narrow,
                           "⚔", (255, 120, 120), "ATK",
                           str(cdata.get('atk', '?')), (255, 140, 140),
                           bg=(40, 24, 24))
                _stat_cell(surf, pad_x + 2 * (narrow + 3), row2_y, narrow,
                           "🛡", (120, 160, 255), "DEF",
                           str(cdata.get('def', '?')), (140, 170, 255),
                           bg=(22, 28, 50))

                effect_y = row2_y + 30
            else:
                subtype = cdata.get('type', ctype)
                _stat_cell(surf, pad_x, grid_y, cell_w,
                           "◈", tc, "TIPO", ctype, tc)
                _stat_cell(surf, pad_x + cell_w + 4, grid_y, cell_w,
                           "◆", DIM, "SUB", subtype, DIM)
                effect_y = grid_y + 32

            pygame.draw.line(surf, (*SEP, 50), (rx + 10, effect_y), (SW - 10, effect_y), 1)
            effect = cdata.get('text', '')
            if effect:
                draw_text_wrap(surf, effect, rx + 12, effect_y + 6, RW - 24,
                               (175, 178, 185), size=9)

        else:
            # Placeholder
            img_y = TH + 20 + 100
            fill_rect_alpha(surf, rx + 14, TH + 20, SW - 14, TH + 220, (25, 27, 36, 255))
            rrect_outline(surf, rx + 14, TH + 20, SW - 14, TH + 220, 8, (*SEP, 70), 1)
            draw_text(surf, "Pasa el cursor", cx, img_y - 12, DIM, size=11, anchor="center")
            draw_text(surf, "sobre una carta", cx, img_y + 12, DIM, size=11, anchor="center")

        # ── Duel Log ─────────────────────────────────────────────────────
        log_top = SH - 200
        pygame.draw.line(surf, (*SEP, 90), (rx + 10, log_top), (SW - 10, log_top), 1)
        draw_text(surf, "Registro de Duelo", cx, log_top + 14, TEXT,
                  size=11, bold=True, anchor="center")

        for i, (msg, col) in enumerate(reversed(self.duel_log[-7:])):
            ey = log_top + 30 + i * 20
            if ey > SH - 8:
                break
            if i % 2 == 0:
                fill_rect_alpha(surf, rx + 8, ey - 8, SW - 8, ey + 12, (28, 30, 38, 180))
            draw_text(surf, f"• {msg}", rx + 14, ey, col, size=9, anchor="midleft")

    # ── Deck selector ────────────────────────────────────────────────────────

    _SEL_W    = 440
    _SEL_ROW_H = 52

    def _sel_rows(self):
        pw    = self._SEL_W
        x1    = SW // 2 - pw // 2
        rh    = self._SEL_ROW_H
        top_y = SH // 2 - len(self._all_decks) * (rh + 6) // 2
        rows  = []
        for i, d in enumerate(self._all_decks):
            ry1 = top_y + i * (rh + 6)
            rows.append((d, x1, ry1, x1 + pw, ry1 + rh))
        return rows

    def _draw_deck_selector(self, surf: pygame.Surface):
        surf.fill((10, 12, 18))

        cx  = SW // 2
        pw  = self._SEL_W
        ph  = max(200, len(self._all_decks) * (self._SEL_ROW_H + 6) + 100)
        py1 = SH // 2 - ph // 2
        py2 = py1 + ph

        rrect_filled (surf, cx - pw//2 - 20, py1 - 20, cx + pw//2 + 20, py2 + 20,
                      14, (28, 32, 42))
        rrect_outline(surf, cx - pw//2 - 20, py1 - 20, cx + pw//2 + 20, py2 + 20,
                      14, (*SEP, 150), 1)

        draw_text(surf, "Elegir Deck", cx, py1 - 4, TEXT,
                  size=18, bold=True, anchor="midbottom")

        if not self._all_decks:
            draw_text(surf, "No hay decks guardados.", cx, SH // 2 - 12, DIM,
                      size=13, anchor="center")
            draw_text(surf, "Creá uno en el Deck Builder.", cx, SH // 2 + 12, DIM,
                      size=13, anchor="center")
        else:
            for d, x1, y1, x2, y2 in self._sel_rows():
                hov = in_rect(self.mx, self.my, x1, y1, x2, y2)
                rrect_filled (surf, x1, y1, x2, y2, 8, BTN_HOV if hov else BTN)
                border = (*BLUE_N, 150) if hov else (*SEP, 80)
                rrect_outline(surf, x1, y1, x2, y2, 8, border, 1)

                ry = (y1 + y2) // 2
                draw_text(surf, d.get('name', '?'), x1 + 16, ry - 8,
                          TEXT, size=13, bold=True, anchor="midleft")
                draw_text(surf, f"{d.get('card_count', 0)} cartas",
                          x1 + 16, ry + 10, DIM, size=9, anchor="midleft")
                arr_col = (*BLUE_N, 200) if hov else (*DIM, 180)
                draw_text(surf, "▶", x2 - 20, ry, arr_col, size=12, anchor="center")

        draw_text(surf, "ESC · Volver al menú", cx, py2 + 28, DIM,
                  size=9, anchor="center")

    def _handle_sel_click(self, x, y):
        for d, x1, y1, x2, y2 in self._sel_rows():
            if in_rect(x, y, x1, y1, x2, y2):
                self._load_deck(d)
                return

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _log(self, msg: str, color=None):
        self.duel_log.append((msg, color or DIM))
        if len(self.duel_log) > 50:
            self.duel_log.pop(0)

    def _go_menu(self):
        from menu_view import MenuView
        self.game.show_view(MenuView(self.game))


# ── Shared panel helpers ──────────────────────────────────────────────────────

def _av_box(surf, cx, y1, y2, color, label):
    x1, x2 = cx - (LW // 2 - 14), cx + (LW // 2 - 14)
    bg = tuple(max(0, c - 30) for c in color[:3])
    rrect_filled(surf, x1, y1, x2, y2, 8, bg)
    for exp, al in [(5, 14), (3, 45), (1, 100)]:
        rrect_outline(surf, x1 - exp, y1 - exp, x2 + exp, y2 + exp,
                      8 + exp, (*color, al), 1)
    rrect_outline(surf, x1, y1, x2, y2, 8, (*color, 200), 2)
    draw_text(surf, label, cx, (y1 + y2) // 2, (*color, 180),
              size=26, bold=True, anchor="center")


def _draw_phases(surf, y_start, current_phase):
    cx_panel = LW // 2
    pw_tot   = LW - 20
    pill_w   = (pw_tot - (len(_PHASES) - 1) * 4) // len(_PHASES)
    pill_h   = 20
    ph_y     = y_start + pill_h // 2

    for i, ph in enumerate(_PHASES):
        px1 = 10 + i * (pill_w + 4)
        px2 = px1 + pill_w
        active = (ph == current_phase)
        if active:
            for exp, al in [(4, 10), (2, 28), (1, 55)]:
                fill_rect_alpha(surf, px1 - exp, ph_y - pill_h//2 - exp,
                                px2 + exp, ph_y + pill_h//2 + exp, (*GOLD, al))
            rrect_filled (surf, px1, ph_y - pill_h//2, px2, ph_y + pill_h//2, 5, (58, 50, 16))
            rrect_outline(surf, px1, ph_y - pill_h//2, px2, ph_y + pill_h//2, 5, (*GOLD, 220), 1)
        else:
            rrect_filled (surf, px1, ph_y - pill_h//2, px2, ph_y + pill_h//2, 5, (34, 37, 46))
            rrect_outline(surf, px1, ph_y - pill_h//2, px2, ph_y + pill_h//2, 5, (*SEP, 90), 1)
        draw_text(surf, ph, (px1 + px2) // 2, ph_y,
                  GOLD if active else DIM, size=7, bold=active, anchor="center")

    ph_name = _PHASE_LABELS.get(current_phase, current_phase)
    draw_text(surf, ph_name, cx_panel, ph_y + pill_h // 2 + 4,
              (*GOLD, 200), size=8, anchor="midtop")

    return ph_y + pill_h // 2 + 20   # next y


def _hsep(surf, y):
    """Thin horizontal separator line across the left panel."""
    pygame.draw.line(surf, (*SEP, 60), (10, y), (LW - 10, y), 1)


def _stat_cell(surf, x1, cy, w, icon, icon_col, label, value, val_col,
               bg=(30, 33, 42)):
    x2 = x1 + w
    y1, y2 = cy - 13, cy + 13
    rrect_filled (surf, x1, y1, x2, y2, 6, bg)
    rrect_outline(surf, x1, y1, x2, y2, 6, (*SEP, 55), 1)
    draw_text(surf, icon,  x1 + 10, cy, icon_col, size=10, anchor="center")
    draw_text(surf, label, x1 + 22, cy - 5, DIM,     size=7, anchor="midleft")
    draw_text(surf, str(value), x1 + 22, cy + 5, val_col, size=9, bold=True, anchor="midleft")
