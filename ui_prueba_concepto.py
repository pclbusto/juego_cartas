#!/usr/bin/env python3
"""
ui_prueba_concepto.py
Componentes SDF con soporte de imagen.

  Fila superior  → sin imagen  (fill sólido)
  Fila inferior  → con imagen  (cover mode, recortada por el SDF)

Ejecutar desde la raíz del proyecto:
    .venv/bin/python ui_prueba_concepto.py
"""
import array
import glob
import arcade
import arcade.gl
import PIL.Image

SW, SH = 2560, 1080
TITLE   = "UI Components — Shader SDF + imágenes"
FPS     = 60

BG          = ( 15,  17,  22)
SEP         = ( 52,  58,  72)
TEXT        = (222, 226, 234)
DIM         = ( 95, 103, 118)

BTN_BG      = ( 38,  43,  54)
BTN_HOV     = ( 55,  62,  76)
BTN_BORDER  = (100, 108, 125)
BTN_BORDER_H= (140, 148, 165)

LBL_BG      = ( 24,  27,  36)
LBL_HOV     = ( 40,  45,  58)
LBL_BORDER  = (120, 130, 150)
LBL_BORDER_H= (165, 175, 200)

PANEL_BG        = ( 32,  36,  46)
PANEL_TITLE_BG  = ( 18,  20,  26)
PANEL_BORDER    = BTN_BORDER

FONT_SZ = 13
RADIUS  = 10

# ── Shader SDF ────────────────────────────────────────────────────────────────

_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
uniform vec2 u_res;
uniform vec2 u_offset;
void main() {
    vec2 pos = in_pos + u_offset;
    vec2 ndc = pos / u_res * 2.0 - 1.0;
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_uv = in_uv;
}
"""

_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_color;

uniform vec2      u_size;
uniform float     u_radius;
uniform float     u_bw;
uniform vec4      u_fill;
uniform vec4      u_fill_title;
uniform float     u_title_height;
uniform vec4      u_border;
uniform sampler2D u_tex;
uniform int       u_has_tex;   // 0 = fill sólido, 1 = textura
uniform float     u_comp_ar;   // aspect ratio del componente (w/h)
uniform float     u_tex_ar;    // aspect ratio de la textura   (w/h)

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

void main() {
    vec2  p     = (v_uv - 0.5) * u_size;
    float d     = sdRoundBox(p, u_size * 0.5, u_radius);
    float aa    = fwidth(d);
    float outer = smoothstep( aa, -aa, d);
    float inner = smoothstep( aa, -aa, d + u_bw);

    vec4 content;
    if (u_has_tex == 1) {
        // Cover mode: escala para llenar, recorta el exceso, centra
        vec2 uv = v_uv;
        if (u_tex_ar > u_comp_ar) {
            // textura más ancha → recortar laterales
            uv.x = 0.5 + (v_uv.x - 0.5) * (u_comp_ar / u_tex_ar);
        } else {
            // textura más alta → recortar arriba/abajo
            uv.y = 0.5 + (v_uv.y - 0.5) * (u_tex_ar / u_comp_ar);
        }
        content = texture(u_tex, uv);
    } else {
        if (u_title_height > 0.0 && (1.0 - v_uv.y) * u_size.y <= u_title_height) {
            content = u_fill_title;
        } else {
            content = u_fill;
        }
    }

    f_color = content * inner + u_border * (outer - inner);
}
"""

_prog_cache = None

def _get_prog(ctx):
    global _prog_cache
    if _prog_cache is None:
        _prog_cache = ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)
    return _prog_cache


def _load_ctx_tex(ctx, path: str):
    """Carga una imagen PIL como textura OpenGL. Retorna None si falla."""
    try:
        img = PIL.Image.open(path).convert("RGBA")
        tex = ctx.texture(img.size, components=4, data=img.tobytes())
        tex.filter = ctx.LINEAR, ctx.LINEAR
        return tex, img.width / img.height
    except Exception:
        return None, 1.0


# ── Base SDF component ────────────────────────────────────────────────────────

class _SDFComponent:
    def __init__(self, ctx, cx, cy, w, h,
                 fill, fill_hov, border, border_hov, radius,
                 image_path=None, show_border=True):
        self.ctx         = ctx
        self.cx, self.cy = cx, cy
        self.w,  self.h  = w, h
        self.fill        = fill
        self.fill_hov    = fill_hov
        self.border      = border
        self.border_hov  = border_hov
        self.radius      = radius
        self.show_border = show_border
        self.hovered     = False
        self.active      = False
        self.active_color = None
        self.font_size    = None
        self._tex        = None
        self._tex_ar     = 1.0
        self.draw_offset = (0.0, 0.0)

        if image_path:
            self._tex, self._tex_ar = _load_ctx_tex(ctx, image_path)

        self._build_geo()

    def _build_geo(self):
        x1, y1 = self.cx - self.w / 2, self.cy - self.h / 2
        x2, y2 = self.cx + self.w / 2, self.cy + self.h / 2
        vbo = self.ctx.buffer(data=array.array('f', [
            x1, y1, 0.0, 0.0,
            x2, y1, 1.0, 0.0,
            x1, y2, 0.0, 1.0,
            x2, y2, 1.0, 1.0,
        ]))
        self._geo = self.ctx.geometry(
            [arcade.gl.BufferDescription(vbo, '2f 2f', ['in_pos', 'in_uv'])],
            mode=self.ctx.TRIANGLE_STRIP,
        )

    def contains(self, x, y):
        ox, oy = self.draw_offset
        return abs((x - ox) - self.cx) <= self.w / 2 and abs((y - oy) - self.cy) <= self.h / 2

    def on_mouse_motion(self, x, y):
        self.hovered = self.contains(x, y)

    def _draw_sdf(self):
        prog   = _get_prog(self.ctx)
        fill   = self.fill_hov   if self.hovered else self.fill
        border = self.border_hov if self.hovered else self.border

        prog['u_res']      = (float(SW), float(SH))
        prog['u_size']     = (float(self.w), float(self.h))
        prog['u_radius']   = float(self.radius)
        prog['u_bw']       = 1.5 if self.show_border else 0.0
        
        # Color selection
        if self.active and self.active_color:
            fill = self.active_color
        else:
            fill = self.fill_hov if self.hovered else self.fill
            
        border = self.border_hov if self.hovered else self.border

        prog['u_fill']     = tuple(c / 255.0 for c in (*fill,   255))
        prog['u_border']   = tuple(c / 255.0 for c in (*border, 255))
        prog['u_comp_ar']  = float(self.w) / float(self.h)

        try:
            prog['u_offset'] = getattr(self, 'draw_offset', (0.0, 0.0))
        except KeyError:
            pass

        try:
            prog['u_title_height'] = float(getattr(self, 'title_height', 0.0))
            fill_t = getattr(self, 'fill_title', fill)
            prog['u_fill_title'] = tuple(c / 255.0 for c in (*fill_t, 255))
        except KeyError:
            pass

        if self._tex:
            self._tex.use(0)
            prog['u_tex']     = 0
            prog['u_has_tex'] = 1
            prog['u_tex_ar']  = self._tex_ar
        else:
            prog['u_has_tex'] = 0
            prog['u_tex_ar']  = 1.0

        self.ctx.enable(self.ctx.BLEND)
        self._geo.render(prog)


# ── Componentes concretos ─────────────────────────────────────────────────────

class ShaderPanel(_SDFComponent):
    def __init__(self, ctx, cx, cy, w, h, title=""):
        super().__init__(ctx, cx, cy, w, h,
                         PANEL_BG, PANEL_BG, PANEL_BORDER, PANEL_BORDER,
                         RADIUS)
        self.title = title
        if title:
            self.title_height = 45.0
            self.fill_title   = PANEL_TITLE_BG
        else:
            self.title_height = 0.0
            self.fill_title   = PANEL_BG
            
        self.children = []
        self.scroll_y = 0.0
        self.max_scroll = 0.0

    def add_child(self, child):
        self.children.append(child)
        self.update_layout()
        
    def update_layout(self):
        if not self.children:
            self.max_scroll = 0.0
            return
        min_y = min(c.cy - c.h / 2 for c in self.children)
        max_y = max(c.cy + c.h / 2 for c in self.children)
        content_h = max_y - min_y
        available_h = self.h - self.title_height
        self.max_scroll = max(0.0, content_h - available_h + 40) # padding inferior

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.contains(x, y) and self.max_scroll > 0:
            self.scroll_y -= scroll_y * 30
            self.scroll_y = max(0.0, min(self.scroll_y, self.max_scroll))
            return True
        return False

    def on_mouse_motion(self, x, y):
        super().on_mouse_motion(x, y)
        if self.contains(x, y):
            bx = self.cx - self.w / 2
            by = self.cy - self.h / 2
            bw = self.w
            bh = self.h - self.title_height
            # Solo pasar hover si está en el cuerpo visible
            if bx <= x <= bx + bw and by <= y <= by + bh:
                for c in self.children:
                    c.on_mouse_motion(x, y)
            else:
                for c in self.children:
                    c.hovered = False
        else:
            for c in self.children:
                c.hovered = False

    def draw(self):
        self._draw_sdf()
        if self.title:
            arcade.draw_text(self.title, 
                             self.cx - self.w / 2 + 24, 
                             self.cy + self.h / 2 - 22.5, 
                             TEXT,
                             font_size=15, bold=True,
                             anchor_x="left", anchor_y="center")
                             
        if self.children:
            bx = int(self.cx - self.w / 2)
            by = int(self.cy - self.h / 2)
            bw = int(self.w)
            bh = int(self.h - self.title_height)
            
            # En Arcade, Scissor Test se activa y desactiva asignando la propiedad
            try:
                self.ctx.scissor = (bx, by, bw, bh)
                for child in self.children:
                    child.draw_offset = (0.0, self.scroll_y)
                    child.draw()
            finally:
                self.ctx.scissor = None

class ShaderButton(_SDFComponent):
    def __init__(self, ctx, cx, cy, w, h, label, image_path=None):
        super().__init__(ctx, cx, cy, w, h,
                         BTN_BG, BTN_HOV, BTN_BORDER, BTN_BORDER_H,
                         RADIUS, image_path)
        self.label = label

    def draw(self):
        self._draw_sdf()
        if self.label:
            ox, oy = self.draw_offset
            arcade.draw_text(self.label, self.cx + ox, self.cy + oy, TEXT,
                             font_size=self.font_size if self.font_size is not None else FONT_SZ,
                             anchor_x="center", anchor_y="center",
                             bold=True)


class ShaderPill(_SDFComponent):
    def __init__(self, ctx, cx, cy, w, h, label, image_path=None, border=True):
        super().__init__(ctx, cx, cy, w, h,
                         LBL_BG, LBL_HOV, LBL_BORDER, LBL_BORDER_H,
                         h // 2, image_path, show_border=border)
        self.label = label

    def draw(self):
        self._draw_sdf()
        if self.label:
            ox, oy = self.draw_offset
            arcade.draw_text(self.label, self.cx + ox, self.cy + oy, TEXT,
                             font_size=FONT_SZ - 1,
                             anchor_x="center", anchor_y="center")


class ShaderCircle(_SDFComponent):
    def __init__(self, ctx, cx, cy, diameter, label, image_path=None, border=True):
        super().__init__(ctx, cx, cy, diameter, diameter,
                         LBL_BG, LBL_HOV, LBL_BORDER, LBL_BORDER_H,
                         diameter // 2, image_path, show_border=border)
        self.label = label

    def draw(self):
        self._draw_sdf()
        if self.label:
            ox, oy = self.draw_offset
            arcade.draw_text(self.label, self.cx + ox, self.cy + oy, TEXT,
                             font_size=FONT_SZ,
                             anchor_x="center", anchor_y="center")


class TextComponent:
    """Componente de texto nativo con opciones de ajuste de línea."""
    def __init__(self, cx, cy, text, w, font_size=FONT_SZ, color=TEXT, align="left", multiline=False):
        self.cx, self.cy = cx, cy
        self.w = w
        self.draw_offset = (0.0, 0.0)
        self.hovered = False
        self.color = color
        self.align = align
        self.multiline = multiline
        self.font_size = font_size
        
        self._build_text(text)

    def _build_text(self, text):
        self._text_obj = arcade.Text(
            text, 0, 0, self.color, font_size=self.font_size,
            width=int(self.w) if self.multiline else 0,
            align=self.align, multiline=self.multiline,
            anchor_x="center", anchor_y="center"
        )
        self.h = self._text_obj.content_height
        if not self.multiline:
            self.w = self._text_obj.content_width

    def on_mouse_motion(self, x, y):
        pass

    def contains(self, x, y):
        ox, oy = self.draw_offset
        return abs((x - ox) - self.cx) <= self.w / 2 and abs((y - oy) - self.cy) <= self.h / 2

    def draw(self):
        ox, oy = self.draw_offset
        self._text_obj.position = (self.cx + ox, self.cy + oy)
        self._text_obj.draw()


# ── Vista ─────────────────────────────────────────────────────────────────────

BTN_LABELS  = ["OK", "Cancelar", "Fase de Batalla",
               "Pasar Turno", "Activar Efecto", "Ataque Directo"]
PILL_LABELS = ["Monstruo", "Hechizo", "Nivel 4",
               "ATK 1800", "WATER", "Efecto"]
CIRC_LABELS = ["4", "★", "?", "12", "●", "∞"]


class BoardView(arcade.View):

    def __init__(self):
        super().__init__()
        self._all: list[_SDFComponent] = []

    def on_show_view(self):
        ctx     = self.window.ctx
        images  = sorted(glob.glob("images/*.jpg"))[:6]

        # Dimensiones
        btn_h  = 48
        pill_h = 36
        circ_d = 52
        gap    = 14
        pad_x  = 40

        # Centros de columna (3 columnas)
        cx_b = SW // 6
        cx_p = SW // 2
        cx_c = 5 * SW // 6

        # ── Paneles de fondo ───────────────────
        panel_w = SW // 3 - 60
        panel_h = SH - 120
        panel_acciones = ShaderPanel(ctx, cx_b, SH // 2, panel_w, panel_h, title="Panel de Acciones")
        panel_info     = ShaderPanel(ctx, cx_p, SH // 2, panel_w, panel_h, title="Panel de Información")
        panel_circulos = ShaderPanel(ctx, cx_c, SH // 2, panel_w, panel_h, title="Registro de Batalla")

        self._all.extend([panel_acciones, panel_info, panel_circulos])

        def populate_panel(panel, labels, item_h, make_item_fn):
            body_top = panel.cy + panel.h / 2 - panel.title_height
            current_y = body_top - gap - item_h / 2
            for i, lbl in enumerate(labels):
                img = images[i % len(images)] if images and i % 2 == 1 else None
                item = make_item_fn(panel.cx, current_y, lbl, img)
                panel.add_child(item)
                current_y -= (item_h + gap)

        # Multiplicamos el contenido para obligar al scroll
        many_btns  = (BTN_LABELS + ["Bajar Defensa", "Rendirse", "Ver Extra Deck"]) * 3
        many_pills = (PILL_LABELS + ["Trampa", "Continua", "Tierra"]) * 3
        many_circs = (CIRC_LABELS + ["X", "Y", "Z", "W"]) * 3

        def make_btn(cx, cy, lbl, img):
            w = max(160, len(lbl) * 10 + pad_x * 2)
            return ShaderButton(ctx, cx, cy, w, btn_h, lbl, image_path=img)
        populate_panel(panel_acciones, many_btns, btn_h, make_btn)

        def make_pill(cx, cy, lbl, img):
            w = max(100, len(lbl) * 10 + 36)
            return ShaderPill(ctx, cx, cy, w, pill_h, lbl, image_path=img)
        populate_panel(panel_info, many_pills, pill_h, make_pill)

        # Tercer panel: Mezcla de Texto Descriptivo y Círculos
        body_top = panel_circulos.cy + panel_circulos.h / 2 - panel_circulos.title_height
        curr_y = body_top - gap

        texto_largo = (
            "Puedes instanciar componentes como PanelLabel para inyectar descripciones "
            "extensas en tu UI. Al estar subordinado al panel, hereda el límite visual "
            "gracias al Scissor Test y procesa adecuadamente el offset.\n\n"
            "El componente calcula su altura de forma exacta basándose en el fuente "
            "para decirle al padre cuál será el límite inferior del scroll de todo "
            "el conjunto de hijos.\n\n"
        ) * 2

        lbl_info = PanelLabel(panel_circulos.cx, 0, texto_largo, panel_w - 60, font_size=15, align="center")
        lbl_info.cy = curr_y - lbl_info.h / 2
        panel_circulos.add_child(lbl_info)
        
        curr_y = lbl_info.cy - lbl_info.h / 2 - gap - circ_d / 2
        
        for i, lbl in enumerate(many_circs):
            img = images[i % len(images)] if images and i % 2 == 1 else None
            circ = ShaderCircle(ctx, panel_circulos.cx, curr_y, circ_d, lbl, image_path=img)
            panel_circulos.add_child(circ)
            curr_y -= (circ_d + gap)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        for c in self._all:
            if hasattr(c, 'on_mouse_scroll'):
                if c.on_mouse_scroll(x, y, scroll_x, scroll_y):
                    break

    def on_mouse_motion(self, x, y, _dx, _dy):
        for c in self._all:
            c.on_mouse_motion(x, y)

    def on_key_press(self, symbol, _mod):
        if symbol == arcade.key.ESCAPE:
            arcade.exit()

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, SW, 0, SH, BG)

        # Etiquetas filas
        for y, lbl in [(int(SH * 0.70), "sin imagen"), (int(SH * 0.28), "con imagen")]:
            arcade.draw_text(lbl, 30, y, DIM,
                             font_size=14, italic=True,
                             anchor_x="left", anchor_y="center", rotation=90)

        for c in self._all:
            c.draw()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    win = arcade.Window(SW, SH, TITLE, fullscreen=False, samples=8)
    win.set_update_rate(1 / FPS)
    win.show_view(BoardView())
    arcade.run()


if __name__ == "__main__":
    main()
