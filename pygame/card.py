import os
import pygame
import PIL.Image
from constants import CARD_WIDTH as CW, CARD_HEIGHT as CH, IMAGES_DIR

_TYPE_COLORS = {
    "MONSTER": (185, 140,  65),
    "SPELL":   ( 55, 130, 175),
    "TRAP":    (160,  55, 100),
}
_CARD_BACK = (28, 22, 55)
_BACK_LINE = (60, 50, 110)

# Module-level thumbnail cache (shared across all views)
_THUMB_CACHE: dict[str, pygame.Surface | None] = {}


def load_thumb(image_name: str) -> pygame.Surface | None:
    if image_name in _THUMB_CACHE:
        return _THUMB_CACHE[image_name]
    surf = None
    path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(path):
        try:
            img  = PIL.Image.open(path).convert('RGBA').resize((CW, CH), PIL.Image.LANCZOS)
            surf = pygame.image.frombytes(img.tobytes(), (CW, CH), 'RGBA')
        except Exception:
            pass
    _THUMB_CACHE[image_name] = surf
    return surf


def load_full(image_name: str, target_w: int, target_h: int) -> pygame.Surface | None:
    """Load full-size image scaled to fit target area while keeping aspect ratio."""
    path = os.path.join(IMAGES_DIR, image_name)
    if not os.path.exists(path):
        return None
    try:
        img = PIL.Image.open(path).convert('RGBA')
        scale = min(target_w / img.width, target_h / img.height)
        nw = int(img.width  * scale)
        nh = int(img.height * scale)
        img = img.resize((nw, nh), PIL.Image.LANCZOS)
        return pygame.image.frombytes(img.tobytes(), (nw, nh), 'RGBA')
    except Exception:
        return None


class Card:
    def __init__(self, card_data: dict = None):
        self.card_data    = card_data or {}
        self.name         = self.card_data.get('name', 'Carta')
        self.card_type    = self.card_data.get('card_type', 'MONSTER').upper()
        self.face_color   = _TYPE_COLORS.get(self.card_type, (120, 100, 80))
        self.face_up      = True
        self.in_attack    = True
        self.current_zone = None

        img_name   = self.card_data.get('image_name', '')
        self.thumb = load_thumb(img_name) if img_name else None

        # Position (center, pygame y-down)
        self.x: float = 0.0
        self.y: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - CW / 2), int(self.y - CH / 2), CW, CH)

    def collides_with_point(self, px, py) -> bool:
        return self.rect.collidepoint(px, py)

    def draw(self, surf: pygame.Surface):
        if not self.face_up:
            self._draw_back(surf)
            return

        rx, ry = int(self.x - CW / 2), int(self.y - CH / 2)

        if self.thumb:
            surf.blit(self.thumb, (rx, ry))
        else:
            pygame.draw.rect(surf, self.face_color, pygame.Rect(rx, ry, CW, CH))

        # Inner border
        pygame.draw.rect(surf, (0, 0, 0),
                         pygame.Rect(rx + 2, ry + 2, CW - 4, CH - 4), 1)

        # Name strip (only when no image, or always for context)
        if not self.thumb:
            strip = pygame.Surface((CW, 22), pygame.SRCALPHA)
            strip.fill((0, 0, 0, 150))
            surf.blit(strip, (rx, ry + CH - 22))
            from draw_utils import draw_text
            draw_text(surf, self.name, rx + CW // 2, ry + CH - 11,
                      (255, 255, 255), size=8, bold=True, anchor="center")

    def _draw_back(self, surf: pygame.Surface):
        rx, ry = int(self.x - CW / 2), int(self.y - CH / 2)
        s = pygame.Surface((CW, CH), pygame.SRCALPHA)
        s.fill((*_CARD_BACK, 255))
        # diagonal lines
        for offset in range(0, (CW + CH) * 2, 16):
            x0 = min(offset, CW)
            y0 = max(0, offset - CW)
            x1 = max(0, offset - CH)
            y1 = min(offset, CH)
            if x0 >= 0 and y1 >= 0:
                pygame.draw.line(s, (*_BACK_LINE, 55), (x0, 0), (0, y1))
                pygame.draw.line(s, (*_BACK_LINE, 55), (CW - x0, CH), (CW, CH - y1))
        pygame.draw.rect(s, (*_BACK_LINE, 180), pygame.Rect(4, 4, CW - 8, CH - 8), 1)
        # star
        font = pygame.font.SysFont("Arial", 20)
        ts   = font.render("★", True, _BACK_LINE)
        ts.set_alpha(180)
        s.blit(ts, ts.get_rect(center=(CW // 2, CH // 2)))
        surf.blit(s, (rx, ry))
