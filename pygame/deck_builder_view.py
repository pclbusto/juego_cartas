"""Deck Builder — browse all cards, manage decks."""
import os
import sys
import pygame
import PIL.Image

import constants
from card import load_thumb
from draw_utils import (
    BG_DEEP, PANEL_BG, SEP, TEXT, DIM, GOLD, BLUE_N, RED_N,
    BTN, BTN_HOV, BTN_ACT, C_MONSTER, C_SPELL, C_TRAP, TYPE_COLOR,
    rrect_filled, rrect_outline, fill_rect_alpha,
    draw_text, draw_text_wrap, draw_btn, in_rect, get_font,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)
from database import DatabaseManager

SW, SH  = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
CW, CH  = constants.CARD_WIDTH, constants.CARD_HEIGHT

# Layout
SIDE_W   = 300          # right deck panel width
GRID_X   = 12           # left edge of card grid
GRID_Y   = 84           # top of card grid
COLS     = max(1, (SW - SIDE_W - GRID_X * 2) // (CW + 8))
ROWS_VIS = max(1, (SH - GRID_Y - 12) // (CH + 8))
CARD_GAP = 8

# Filter bar
FILT_H   = 40


class DeckBuilderView:
    def __init__(self, game):
        self.game = game
        db_path   = os.path.join(BASE_DIR, 'yugioh.db')
        self.db   = DatabaseManager(db_path)

        self.all_cards:  list[dict] = []
        self.filtered:   list[dict] = []
        self.scroll_top  = 0          # first visible row index

        self.decks:      list[dict] = []
        self.active_deck: dict | None = None
        self.deck_cards: list[dict] = []

        self.search_text = ""
        self.search_active = False
        self.filter_type = "ALL"   # ALL | MONSTER | SPELL | TRAP

        self.mx = self.my = 0
        self.hover_card_data: dict | None = None

        self._load_data()

    # ── Data ─────────────────────────────────────────────────────────────────

    def _load_data(self):
        self.all_cards = self.db.get_cards()
        self.decks     = self.db.get_all_decks()
        self.active_deck = self.decks[0] if self.decks else None
        self._reload_deck_cards()
        self._apply_filter()

    def _reload_deck_cards(self):
        if self.active_deck:
            self.deck_cards = self.db.get_deck_cards(self.active_deck['id'])
        else:
            self.deck_cards = []

    def _apply_filter(self):
        q   = self.search_text.lower().strip()
        ft  = self.filter_type
        out = []
        for c in self.all_cards:
            if ft != "ALL" and c.get('card_type', '').upper() != ft:
                continue
            if q and q not in c.get('name', '').lower():
                continue
            out.append(c)
        self.filtered   = out
        self.scroll_top = 0

    # ── Grid helpers ─────────────────────────────────────────────────────────

    def _card_rect(self, idx: int) -> pygame.Rect:
        """Rect for card at filtered index, relative to scroll."""
        row = idx // COLS
        col = idx  % COLS
        x   = GRID_X + col * (CW + CARD_GAP)
        y   = GRID_Y + (row - self.scroll_top) * (CH + CARD_GAP)
        return pygame.Rect(x, y, CW, CH)

    def _max_scroll(self) -> int:
        total_rows = (len(self.filtered) + COLS - 1) // COLS
        return max(0, total_rows - ROWS_VIS)

    def _visible_range(self):
        start = self.scroll_top * COLS
        end   = start + ROWS_VIS * COLS
        return start, min(end, len(self.filtered))

    # ── Deck panel geometry ───────────────────────────────────────────────────

    _DPX1 = SW - SIDE_W      # left edge of deck panel
    _DPY1 = 84               # top (below filter bar)
    _ENTRY_H = 22

    def _deck_entry_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self._DPX1 + 4, self._DPY1 + 4 + i * self._ENTRY_H,
                           SIDE_W - 8, self._ENTRY_H)

    # ── Events ───────────────────────────────────────────────────────────────

    def on_enter(self): pass
    def on_exit(self):  pass

    def on_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mx, self.my = event.pos
            self._update_hover()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._on_click(*event.pos)
            elif event.button == 4:   # scroll up
                self.scroll_top = max(0, self.scroll_top - 1)
            elif event.button == 5:   # scroll down
                self.scroll_top = min(self._max_scroll(), self.scroll_top + 1)

        elif event.type == pygame.KEYDOWN:
            if self.search_active:
                if event.key == pygame.K_BACKSPACE:
                    self.search_text = self.search_text[:-1]
                    self._apply_filter()
                elif event.key == pygame.K_RETURN:
                    self.search_active = False
                elif event.key == pygame.K_ESCAPE:
                    self.search_text = ""
                    self.search_active = False
                    self._apply_filter()
                else:
                    if event.unicode.isprintable():
                        self.search_text += event.unicode
                        self._apply_filter()
            else:
                if event.key == pygame.K_ESCAPE:
                    self._go_menu()

    def _update_hover(self):
        self.hover_card_data = None
        start, end = self._visible_range()
        for i in range(start, end):
            r = self._card_rect(i)
            if r.collidepoint(self.mx, self.my):
                self.hover_card_data = self.filtered[i]
                break

    def _on_click(self, x, y):
        # Back button
        if in_rect(x, y, 8, 8, 120, 44):
            self._go_menu()
            return

        # Search box
        if in_rect(x, y, 132, 12, SW - SIDE_W - 12, 52):
            self.search_active = True
            return

        # Filter buttons
        fx = SW // 2 - 200
        for ft in ["ALL", "MONSTER", "SPELL", "TRAP"]:
            if in_rect(x, y, fx, 12, fx + 80, 52):
                self.filter_type = ft
                self._apply_filter()
                return
            fx += 88

        # Card grid — add to deck
        start, end = self._visible_range()
        for i in range(start, end):
            r = self._card_rect(i)
            if r.collidepoint(x, y):
                self._add_card(self.filtered[i])
                return

        # Deck panel entries — remove on right click handled separately
        if x >= self._DPX1:
            for i, entry in enumerate(self.deck_cards):
                r = self._deck_entry_rect(i)
                if r.collidepoint(x, y):
                    # Double-click or just click = remove one copy
                    self._remove_card(entry)
                    return

            # New deck button
            nd_y = self._DPY1 + 4 + len(self.deck_cards) * self._ENTRY_H + 10
            if in_rect(x, y, self._DPX1 + 4, nd_y, self._DPX1 + SIDE_W - 8, nd_y + 28):
                self._new_deck()

    # ── Deck operations ──────────────────────────────────────────────────────

    def _add_card(self, card: dict):
        if not self.active_deck:
            return
        self.db.add_card_to_deck(self.active_deck['id'], card['cid'])
        self._reload_deck_cards()

    def _remove_card(self, entry: dict):
        if not self.active_deck:
            return
        self.db.remove_card_from_deck(self.active_deck['id'], entry['cid'])
        self._reload_deck_cards()

    def _new_deck(self):
        # Simple: create deck named "Deck N"
        n = len(self.decks) + 1
        name = f"Deck {n}"
        self.db.create_deck(name)
        self.decks = self.db.get_all_decks()
        self.active_deck = next((d for d in self.decks if d['name'] == name), self.decks[-1])
        self._reload_deck_cards()

    def _select_deck(self, deck: dict):
        self.active_deck = deck
        self._reload_deck_cards()

    # ── Draw ─────────────────────────────────────────────────────────────────

    def on_update(self, dt): pass

    def on_draw(self, surf: pygame.Surface):
        surf.fill(BG_DEEP)

        # ── Top bar ──────────────────────────────────────────────────────────
        pygame.draw.rect(surf, PANEL_BG, pygame.Rect(0, 0, SW, FILT_H + 24))
        pygame.draw.line(surf, SEP, (0, FILT_H + 24), (SW, FILT_H + 24), 1)

        # Back button
        hov_back = in_rect(self.mx, self.my, 8, 8, 120, 44)
        draw_btn(surf, 64, 32, 112, 32, "← Menú", hovered=hov_back)

        # Search box
        sb_x1, sb_x2 = 132, SW - SIDE_W - 12
        sb_y1, sb_y2 = 12, 52
        rrect_filled(surf, sb_x1, sb_y1, sb_x2, sb_y2, 6,
                     (35, 38, 48) if self.search_active else (28, 31, 40))
        rrect_outline(surf, sb_x1, sb_y1, sb_x2, sb_y2, 6,
                      (*BLUE_N, 180) if self.search_active else (*SEP, 80), 1)
        display = (self.search_text + "|") if self.search_active else (self.search_text or "Buscar carta...")
        col = TEXT if self.search_text else DIM
        draw_text(surf, display, sb_x1 + 10, (sb_y1 + sb_y2) // 2, col,
                  size=11, anchor="midleft")

        # Filter buttons
        fx = SW // 2 - 200
        _FILT_LABELS = [("ALL", "Todo"), ("MONSTER", "Monstruos"),
                        ("SPELL", "Hechizos"), ("TRAP", "Trampa")]
        _FILT_COLORS = {"ALL": DIM, "MONSTER": C_MONSTER, "SPELL": C_SPELL, "TRAP": C_TRAP}
        for ft, lbl in _FILT_LABELS:
            hov = in_rect(self.mx, self.my, fx, 12, fx + 80, 52)
            active = (self.filter_type == ft)
            col = _FILT_COLORS[ft]
            rrect_filled(surf, fx, 12, fx + 80, 52, 6,
                         (*col, 55) if active else (BTN_HOV if hov else BTN))
            rrect_outline(surf, fx, 12, fx + 80, 52, 6,
                          (*col, 200) if active else (*SEP, 60), 1)
            draw_text(surf, lbl, fx + 40, 32, TEXT if active else DIM,
                      size=10, bold=active, anchor="center")
            fx += 88

        # ── Card grid ────────────────────────────────────────────────────────
        start, end = self._visible_range()
        for i in range(start, end):
            card  = self.filtered[i]
            r     = self._card_rect(i)
            if r.bottom < GRID_Y or r.top > SH:
                continue
            thumb = load_thumb(card.get('image_name', ''))
            if thumb:
                surf.blit(thumb, r.topleft)
            else:
                tc = TYPE_COLOR.get(card.get('card_type', ''), DIM)
                pygame.draw.rect(surf, tc, r)

            # hover highlight
            if self.hover_card_data and self.hover_card_data.get('cid') == card.get('cid'):
                rrect_outline(surf, r.x - 3, r.y - 3, r.right + 3, r.bottom + 3,
                              4, (*BLUE_N, 200), 2)

        # Count
        draw_text(surf, f"{len(self.filtered)} cartas",
                  GRID_X, GRID_Y - 16, DIM, size=9)

        # ── Right deck panel ─────────────────────────────────────────────────
        pygame.draw.rect(surf, PANEL_BG,
                         pygame.Rect(self._DPX1, 0, SIDE_W, SH))
        pygame.draw.line(surf, SEP, (self._DPX1, 0), (self._DPX1, SH), 1)

        # Deck selector header
        deck_name = self.active_deck['name'] if self.active_deck else "Sin deck"
        total     = sum(e.get('quantity', 1) for e in self.deck_cards)
        draw_text(surf, deck_name, self._DPX1 + SIDE_W // 2, 16,
                  GOLD, size=13, bold=True, anchor="center")
        draw_text(surf, f"{total}/60 cartas",
                  self._DPX1 + SIDE_W // 2, 34, DIM, size=9, anchor="center")
        pygame.draw.line(surf, (*SEP, 80),
                         (self._DPX1 + 4, 50), (SW - 4, 50), 1)

        # Deck switcher tabs
        tab_x = self._DPX1 + 4
        for d in self.decks:
            active = (d is self.active_deck or
                      (self.active_deck and d['id'] == self.active_deck['id']))
            tw = SIDE_W // max(len(self.decks), 1) - 4
            hov = in_rect(self.mx, self.my, tab_x, 52, tab_x + tw, 76)
            rrect_filled(surf, tab_x, 52, tab_x + tw, 76, 4,
                         BTN_ACT if active else (BTN_HOV if hov else BTN))
            draw_text(surf, d['name'][:10],
                      tab_x + tw // 2, 64, TEXT, size=9, bold=active, anchor="center")
            if hov and not active:
                # click handled in on_event — store for click detection
                pass
            tab_x += tw + 4

        pygame.draw.line(surf, (*SEP, 80), (self._DPX1 + 4, 78), (SW - 4, 78), 1)

        # Deck card list
        for i, entry in enumerate(self.deck_cards):
            r = self._deck_entry_rect(i)
            if r.bottom > SH - 60:
                break
            hov = r.collidepoint(self.mx, self.my)
            if hov:
                fill_rect_alpha(surf, r.x, r.y, r.right, r.bottom, (*BLUE_N, 30))
            tc = TYPE_COLOR.get(entry.get('card_type', ''), DIM)
            # color dot
            pygame.draw.circle(surf, tc, (r.x + 8, r.centery), 4)
            draw_text(surf, entry.get('name', '?'), r.x + 18, r.centery,
                      TEXT, size=9, anchor="midleft")
            qty = entry.get('quantity', 1)
            draw_text(surf, f"×{qty}", r.right - 4, r.centery,
                      DIM, size=9, anchor="midright")

        # New deck button
        nd_y = self._DPY1 + 4 + len(self.deck_cards) * self._ENTRY_H + 10
        if nd_y < SH - 60:
            hov = in_rect(self.mx, self.my,
                          self._DPX1 + 4, nd_y,
                          self._DPX1 + SIDE_W - 8, nd_y + 28)
            draw_btn(surf, self._DPX1 + SIDE_W // 2, nd_y + 14,
                     SIDE_W - 16, 28, "+ Nuevo Deck", hovered=hov)

        # ── Hover card detail (bottom overlay) ───────────────────────────────
        if self.hover_card_data:
            _draw_hover_detail(surf, self.hover_card_data)

    def _go_menu(self):
        from menu_view import MenuView
        self.game.show_view(MenuView(self.game))


def _draw_hover_detail(surf, card: dict):
    """Small tooltip at the bottom of screen."""
    bh = 80
    by1 = SH - bh
    fill_rect_alpha(surf, 0, by1, SW - SIDE_W, SH, (18, 20, 28, 220))
    pygame.draw.line(surf, (*SEP, 100), (0, by1), (SW - SIDE_W, by1), 1)

    name  = card.get('name', '?')
    ctype = card.get('card_type', 'MONSTER')
    tc    = TYPE_COLOR.get(ctype, DIM)
    draw_text(surf, name, 14, by1 + 14, TEXT, size=12, bold=True)
    draw_text(surf, ctype, 14, by1 + 32, tc, size=9)

    if ctype == 'MONSTER':
        atk = card.get('atk', '?')
        def_ = card.get('def', '?')
        lvl  = card.get('level', 0) or 0
        draw_text(surf, f"Nivel {int(lvl)}   ATK {atk} / DEF {def_}",
                  14, by1 + 48, DIM, size=10)
    effect = card.get('text', '')
    if effect:
        draw_text(surf, effect[:120] + ("…" if len(effect) > 120 else ""),
                  14, by1 + 64, (160, 163, 170), size=8)
