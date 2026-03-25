"""Shared drawing primitives for the pygame port."""
import pygame

# ── Color palette (same as arcade version) ────────────────────────────────────
BG_DEEP   = (27,  30,  35)
BOARD_BG  = (22,  25,  30)
PANEL_BG  = (44,  49,  58)
SEP       = (62,  68,  81)
TEXT      = (230, 232, 238)
DIM       = (110, 115, 128)
GOLD      = (255, 200,  50)
BLUE_N    = (  0, 170, 255)
RED_N     = (255,  76,  76)
GREEN_N   = ( 50, 210,  90)
BTN       = ( 48,  53,  64)
BTN_HOV   = ( 62,  68,  80)
BTN_ACT   = ( 20,  90, 200)
C_MONSTER = (220, 130,  50)
C_SPELL   = ( 80, 180, 255)
C_TRAP    = (210,  90, 110)

ATTR_COLORS = {
    'DARK':  (160,  80, 200),
    'LIGHT': (240, 230,  80),
    'FIRE':  (240, 100,  40),
    'WATER': ( 60, 160, 230),
    'EARTH': (140, 110,  60),
    'WIND':  ( 80, 200, 120),
    'DIVINE':(240, 200,  80),
}

TYPE_COLOR = {'MONSTER': C_MONSTER, 'SPELL': C_SPELL, 'TRAP': C_TRAP}

# ── Font cache ────────────────────────────────────────────────────────────────
_font_cache: dict = {}

def get_font(size: int, bold=False, italic=False) -> pygame.font.Font:
    key = (size, bold, italic)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold, italic=italic)
    return _font_cache[key]

# ── Alpha blit helper ─────────────────────────────────────────────────────────
def _make_surf(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)

# ── Rounded rect ─────────────────────────────────────────────────────────────
def rrect_filled(surf: pygame.Surface, x1, y1, x2, y2, r: int, color: tuple):
    w, h = int(x2 - x1), int(y2 - y1)
    if w <= 0 or h <= 0:
        return
    r = min(r, w // 2, h // 2)
    if len(color) == 4 and color[3] < 255:
        s = _make_surf(w, h)
        pygame.draw.rect(s, color, pygame.Rect(0, 0, w, h), border_radius=r)
        surf.blit(s, (int(x1), int(y1)))
    else:
        pygame.draw.rect(surf, color[:3],
                         pygame.Rect(int(x1), int(y1), w, h), border_radius=r)


def rrect_outline(surf: pygame.Surface, x1, y1, x2, y2, r: int,
                  color: tuple, lw: int = 1):
    w, h = int(x2 - x1), int(y2 - y1)
    if w <= 0 or h <= 0:
        return
    r = min(r, w // 2, h // 2)
    if len(color) == 4 and color[3] < 255:
        s = _make_surf(w, h)
        pygame.draw.rect(s, color, pygame.Rect(0, 0, w, h), lw, border_radius=r)
        surf.blit(s, (int(x1), int(y1)))
    else:
        pygame.draw.rect(surf, color[:3],
                         pygame.Rect(int(x1), int(y1), w, h), lw, border_radius=r)


def fill_rect_alpha(surf: pygame.Surface, x1, y1, x2, y2, color: tuple):
    """Simple filled rect with alpha support."""
    w, h = int(x2 - x1), int(y2 - y1)
    if w <= 0 or h <= 0:
        return
    if len(color) == 4 and color[3] < 255:
        s = _make_surf(w, h)
        s.fill(color)
        surf.blit(s, (int(x1), int(y1)))
    else:
        pygame.draw.rect(surf, color[:3],
                         pygame.Rect(int(x1), int(y1), w, h))


def draw_line_alpha(surf: pygame.Surface, x1, y1, x2, y2, color: tuple, lw=1):
    if len(color) == 4 and color[3] < 255:
        # draw on temp surface
        bx1, bx2 = min(x1, x2) - lw, max(x1, x2) + lw
        by1, by2 = min(y1, y2) - lw, max(y1, y2) + lw
        w, h = int(bx2 - bx1) + 1, int(by2 - by1) + 1
        s = _make_surf(w, h)
        pygame.draw.line(s, color,
                         (int(x1 - bx1), int(y1 - by1)),
                         (int(x2 - bx1), int(y2 - by1)), lw)
        surf.blit(s, (int(bx1), int(by1)))
    else:
        pygame.draw.line(surf, color[:3], (int(x1), int(y1)), (int(x2), int(y2)), lw)


# ── Text ──────────────────────────────────────────────────────────────────────
def draw_text(surf: pygame.Surface, text: str, x, y, color: tuple,
              size=12, bold=False, italic=False, anchor="topleft") -> pygame.Rect:
    if not text:
        return pygame.Rect(int(x), int(y), 0, 0)
    font  = get_font(size, bold=bold, italic=italic)
    alpha = color[3] if len(color) == 4 else 255
    ts    = font.render(str(text), True, color[:3])
    if alpha < 255:
        ts.set_alpha(alpha)
    r = ts.get_rect()
    ix, iy = int(x), int(y)
    if   anchor == "center":     r.center    = (ix, iy)
    elif anchor == "topright":   r.topright  = (ix, iy)
    elif anchor == "midleft":    r.midleft   = (ix, iy)
    elif anchor == "midright":   r.midright  = (ix, iy)
    elif anchor == "midbottom":  r.midbottom = (ix, iy)
    elif anchor == "midbottom":  r.midbottom = (ix, iy)
    elif anchor == "bottomleft": r.bottomleft= (ix, iy)
    elif anchor == "midtop":     r.midtop    = (ix, iy)
    else:                        r.topleft   = (ix, iy)
    surf.blit(ts, r)
    return r


def draw_text_wrap(surf: pygame.Surface, text: str, x, y, max_w: int,
                   color: tuple, size=10, line_h=None) -> int:
    """Word-wrap text. Returns total height used."""
    font   = get_font(size)
    lh     = line_h or (font.get_height() + 3)
    words  = text.split()
    lines  = []
    cur    = ""
    for word in words:
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines):
        draw_text(surf, line, x, y + i * lh, color, size=size)
    return len(lines) * lh


def draw_neon_text(surf: pygame.Surface, text: str, cx, cy, color: tuple,
                   size=28, bold=True):
    """Neon glow text effect — layered renders."""
    for off, alpha in [(2, 35), (1, 70)]:
        draw_text(surf, text, cx, cy, (*color[:3], alpha),
                  size=size + 2, bold=bold, anchor="center")
    draw_text(surf, text, cx, cy, color, size=size, bold=bold, anchor="center")


# ── Button ────────────────────────────────────────────────────────────────────
def draw_btn(surf: pygame.Surface, cx, cy, w, h, label: str,
             hovered=False, active=False, color=None):
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x2, y2 = x1 + int(w),     y1 + int(h)
    if active:
        bg     = color or BTN_ACT
        border = (*( color or BTN_ACT), 200)
    elif hovered:
        bg     = BTN_HOV
        border = (*SEP, 160)
    else:
        bg     = BTN
        border = (*SEP, 80)
    rrect_filled  (surf, x1, y1, x2, y2, 7, bg)
    rrect_outline (surf, x1, y1, x2, y2, 7, border, 1)
    draw_text(surf, label, (x1 + x2) // 2, (y1 + y2) // 2,
              TEXT, size=11, anchor="center")


# ── Misc ──────────────────────────────────────────────────────────────────────
def in_rect(px, py, x1, y1, x2, y2) -> bool:
    return x1 <= px <= x2 and y1 <= py <= y2


def neon_lp(surf: pygame.Surface, cx, cy, lp: int, color: tuple):
    """Life points with neon glow."""
    txt = f"{lp:,}"
    draw_text(surf, txt, cx, cy, (*color[:3], 45), size=32, bold=True, anchor="center")
    draw_text(surf, txt, cx-1, cy-1, (*color[:3], 85), size=31, bold=True, anchor="center")
    draw_text(surf, txt, cx, cy, color, size=29, bold=True, anchor="center")
    pv_x = cx + get_font(29, bold=True).size(txt)[0] // 2 + 6
    draw_text(surf, "PV", pv_x, cy + 10, (*color[:3], 170), size=9, bold=True)


def draw_circle_alpha(surf: pygame.Surface, cx, cy, r, color: tuple, lw=0):
    diam = int(r * 2)
    s = _make_surf(diam + 4, diam + 4)
    pygame.draw.circle(s, color, (diam // 2 + 2, diam // 2 + 2), int(r), lw)
    surf.blit(s, (int(cx - r) - 2, int(cy - r) - 2))
