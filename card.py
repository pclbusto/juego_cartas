import arcade
import constants
import os
import PIL.Image

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

    def __init__(self, card_data=None, name="Carta Básica", card_type="MONSTER"):
        if card_data:
            self.card_data = card_data
            name = card_data.get('name', name)
            card_type = card_data.get('card_type', card_type)
        else:
            self.card_data = {}
            
        face_color = _TYPE_COLORS.get(card_type.upper(), (120, 100, 80))
        super().__init__(CW, CH, face_color)
        self._face_color = face_color   # save — self.color is always white (modulation)
        self.name      = name
        self.card_type = card_type.upper()
        self.face_up   = True
        self.in_attack_position = True
        self.current_zone = None
        self._has_image = False
        self.hovered = False
        self.is_held = False

        # ── Callbacks de eventos ───────────────────────────────────────────
        # Asignar desde la view:
        #   card.on_click       = lambda card: ...
        #   card.on_right_click = lambda card: ...
        #   card.on_drag_start  = lambda card: ...
        #   card.on_drag        = lambda card, x, y: ...
        #   card.on_drop        = lambda card, x, y: ...
        self.on_click       = None
        self.on_right_click = None
        self.on_drag_start  = None
        self.on_drag        = None
        self.on_drop        = None

        # Estado interno para distinguir clic vs arrastre
        self._press_x    = None
        self._press_y    = None
        self._dragging   = False
        _DRAG_THRESHOLD  = 6   # píxeles mínimos para considerar arrastre
        
        # Load local thumbnail if available
        img_name = self.card_data.get('image_name')
        if img_name:
            thumb_path = f"images/{img_name}"
            if os.path.exists(thumb_path):
                tex = arcade.load_texture(thumb_path)
                self.texture = tex
                self.scale = min(CW / tex.width, CH / tex.height)
                self._has_image = True
                
        self._base_scale = self.scale[0] if isinstance(self.scale, tuple) else self.scale
        self._base_y = self.center_y

    def update(self):
        if not hasattr(self, '_base_scale'):
            self._base_scale = self.scale[0] if isinstance(self.scale, tuple) else self.scale
        if not hasattr(self, '_base_y'):
            self._base_y = self.center_y

        current_s = self.scale[0] if isinstance(self.scale, tuple) else self.scale

        if self.is_held:
            # Maintain hover scale while dragging, but don't force Y
            self.scale = current_s + (self._base_scale * 1.15 - current_s) * 0.3
            return

        if self.hovered and self.current_zone is None:
            target_scale = self._base_scale * 1.15
            target_y = self._base_y + 12
        else:
            target_scale = self._base_scale
            target_y = self._base_y

        # Lerp
        self.scale = current_s + (target_scale - current_s) * 0.3
        self.center_y += (target_y - self.center_y) * 0.3

    def draw(self, **kwargs):
        if not self.face_up:
            self._draw_back()
            return

        if getattr(self, '_has_image', False) and hasattr(self, 'texture') and self.texture:
            s_val = self.scale[0] if isinstance(self.scale, tuple) else self.scale
            w = self.texture.width * s_val
            h = self.texture.height * s_val
            x1 = self.center_x - w / 2
            y1 = self.center_y - h / 2
            arcade.draw_texture_rect(self.texture, arcade.LRBT(x1, x1 + w, y1, y1 + h))
            return

        x1 = self.center_x - CW / 2
        y1 = self.center_y - CH / 2
        
        color = getattr(self, '_face_color', getattr(self, 'color', (120, 100, 80)))
        arcade.draw_lrbt_rectangle_filled(x1, x1 + CW, y1, y1 + CH, color)

        # Thin inner border
        x1 = self.center_x - CW / 2 + 2
        y1 = self.center_y - CH / 2 + 2
        x2 = self.center_x + CW / 2 - 2
        y2 = self.center_y + CH / 2 - 2
        arcade.draw_lrbt_rectangle_outline(x1, x2, y1, y2, (0, 0, 0, 80), 1)

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

    # ── Hit test ──────────────────────────────────────────────────────────────

    def contains(self, x, y) -> bool:
        return (abs(x - self.center_x) <= CW / 2 and
                abs(y - self.center_y) <= CH / 2)

    # ── Eventos — llamar desde on_mouse_press/release/drag de la view ────────

    def on_mouse_press(self, x, y, button):
        """Registra el inicio de un posible clic o arrastre."""
        if not self.contains(x, y):
            return False
        if button == 1:
            self._press_x  = x
            self._press_y  = y
            self._dragging = False
            self.is_held   = True
        elif button == 4 and self.on_right_click:
            self.on_right_click(self)
        return True   # consumió el evento

    def on_mouse_drag(self, x, y, dx, dy):
        """Detecta inicio de arrastre y notifica movimiento."""
        if not self.is_held:
            return
        if not self._dragging:
            dist = ((x - self._press_x) ** 2 + (y - self._press_y) ** 2) ** 0.5
            if dist >= 6:
                self._dragging = True
                if self.on_drag_start:
                    self.on_drag_start(self)
        if self._dragging:
            self.center_x = x
            self.center_y = y
            if self.on_drag:
                self.on_drag(self, x, y)

    def on_mouse_release(self, x, y, button):
        """Al soltar: dispara on_click si no hubo arrastre, o on_drop si sí."""
        if button != 1 or not self.is_held:
            return
        self.is_held = False
        if self._dragging:
            self._dragging = False
            if self.on_drop:
                self.on_drop(self, x, y)
        else:
            if self.on_click:
                self.on_click(self)
