import arcade
import constants

CW = constants.CARD_WIDTH
CH = constants.CARD_HEIGHT

# Card face colors per type
_TYPE_COLORS = {
    "MONSTER": (185, 140,  65),
    "SPELL":   ( 55, 130, 175),
    "TRAP":    (160,  55, 100),
}
_TYPE_TEXT = {
    "MONSTER": (255, 230, 150),
    "SPELL":   (200, 240, 255),
    "TRAP":    (255, 200, 220),
}
_CARD_BACK = (28, 22, 55)
_BACK_LINE = (60, 50, 110)


class Card(arcade.SpriteSolidColor):

    def __init__(self, name="Carta Básica", card_type="MONSTER"):
        face_color = _TYPE_COLORS.get(card_type.upper(), (120, 100, 80))
        super().__init__(CW, CH, face_color)
        self.name      = name
        self.card_type = card_type.upper()
        self.face_up   = True
        self.in_attack_position = True
        self.current_zone = None

    def draw(self, **kwargs):
        if not self.face_up:
            self._draw_back()
            return

        super().draw(**kwargs)

        # Thin inner border
        x1 = self.center_x - CW / 2 + 2
        y1 = self.center_y - CH / 2 + 2
        x2 = self.center_x + CW / 2 - 2
        y2 = self.center_y + CH / 2 - 2
        arcade.draw_lrbt_rectangle_outline(x1, x2, y1, y2, (0, 0, 0, 80), 1)

        # Dark name strip at bottom
        strip_h = 22
        sx1 = self.center_x - CW / 2
        sy1 = self.center_y - CH / 2
        arcade.draw_lrbt_rectangle_filled(sx1, sx1 + CW, sy1, sy1 + strip_h,
                                          (0, 0, 0, 140))

        text_col = _TYPE_TEXT.get(self.card_type, (255, 255, 255))
        arcade.draw_text(
            self.name,
            self.center_x, sy1 + strip_h // 2,
            text_col, font_size=8, bold=True,
            anchor_x="center", anchor_y="center",
            width=CW - 6
        )

    def _draw_back(self):
        cx, cy = self.center_x, self.center_y
        x1, y1 = cx - CW / 2, cy - CH / 2
        x2, y2 = cx + CW / 2, cy + CH / 2

        arcade.draw_lrbt_rectangle_filled(x1, x2, y1, y2, _CARD_BACK)

        # Simple diamond pattern on back
        for offset in range(0, max(CW, CH) * 2, 16):
            alpha = 60
            arcade.draw_line(x1 + offset, y1, x1, y1 + offset, (*_BACK_LINE, alpha), 1)
            arcade.draw_line(x2 - offset, y2, x2, y2 - offset, (*_BACK_LINE, alpha), 1)

        arcade.draw_lrbt_rectangle_outline(x1 + 4, x2 - 4, y1 + 4, y2 - 4,
                                           (*_BACK_LINE, 180), 1)
        arcade.draw_text("★", cx, cy, (*_BACK_LINE, 200),
                         font_size=20, anchor_x="center", anchor_y="center")
