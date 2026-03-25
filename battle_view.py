import os
import json
import glob
import uuid
import arcade
import ui_prueba_concepto as ui

RED_PV = (255, 60, 60)
BLUE_PV = (60, 150, 255)
ZONE_BG = (28, 34, 46)
ZONE_BORDER = (80, 95, 120)

class CardZone(ui._SDFComponent):
    def __init__(self, ctx, cx, cy, w, h, image_path=None, **kwargs):
        super().__init__(ctx, cx, cy, w, h, ZONE_BG, (35, 45, 60), ZONE_BORDER, (110, 130, 160), radius=6, image_path=image_path)
    def draw(self):
        self._draw_sdf()

class Avatar(ui._SDFComponent):
    def __init__(self, ctx, cx, cy, size, border_color, image_path=None, **kwargs):
        super().__init__(ctx, cx, cy, size, size, (20, 20, 20), (30, 30, 30), border_color, (255, 255, 255), radius=12, image_path=image_path)
    def draw(self):
        self._draw_sdf()

# Factory
def create_component(ctx, comp_data):
    ctype = comp_data.get("type")
    cx = comp_data.get("cx", ui.SW//2)
    cy = comp_data.get("cy", ui.SH//2)
    w = comp_data.get("w", 100)
    h = comp_data.get("h", 100)
    label = comp_data.get("label", "")
    
    comp = None
    if ctype == "ShaderPanel":
        comp = ui.ShaderPanel(ctx, cx, cy, w, h, title=label)
    elif ctype == "ShaderButton":
        comp = ui.ShaderButton(ctx, cx, cy, w, h, label=label)
    elif ctype == "ShaderPill":
        comp = ui.ShaderPill(ctx, cx, cy, w, h, label=label)
    elif ctype == "ShaderCircle":
        comp = ui.ShaderCircle(ctx, cx, cy, w, label=label)
    elif ctype == "TextComponent":
        multiline = str(comp_data.get("multiline", "False")).lower() == "true"
        comp = ui.TextComponent(cx, cy, label, w, font_size=comp_data.get("font_size", 12), multiline=multiline)
    elif ctype == "CardZone":
        comp = CardZone(ctx, cx, cy, w, h)
    elif ctype == "Avatar":
        comp = Avatar(ctx, cx, cy, w, RED_PV)
        
    if comp:
        comp._id = comp_data.get("id", str(uuid.uuid4()))
        comp._type = ctype
        comp.z = comp_data.get("z", 0)
    return comp

def serialize_component(comp):
    data = {
        "id": getattr(comp, "_id", str(uuid.uuid4())),
        "type": getattr(comp, "_type", comp.__class__.__name__),
        "cx": comp.cx,
        "cy": comp.cy,
        "w": comp.w,
        "h": comp.h if hasattr(comp, 'h') else comp.w,
        "z": getattr(comp, "z", 0)
    }
    if hasattr(comp, "label"): data["label"] = comp.label
    if hasattr(comp, "title"): data["label"] = comp.title
    if hasattr(comp, "_text_obj"): data["font_size"] = comp._text_obj.font_size
    if hasattr(comp, "multiline"): data["multiline"] = str(comp.multiline)
    return data

class BattleView(arcade.View):
    def __init__(self):
        super().__init__()
        self._all = []
        self.edit_mode = False
        self.f3_menu = False
        self.f4_menu = False
        
        # Multi-select vars
        self.selected_comps = set()
        self.first_selected = None
        self.resizing_comp = None
        self.drag_start_pos = None
        self.comp_start_positions = {}
        
        self.marquee_start = None
        self.marquee_end = None
        
        self.editing_prop = None
        self.editing_text = ""

        self.spacing_mode = False
        self.spacing_text = "10"

        self.align_mode = None  # None, 'H' o 'V'

        self.undo_stack = []
        self.MAX_UNDO = 30
        
        self.layout_file = "layout.json"
        self.components_data = []
        self.load_layout()
        
    def push_undo(self):
        self.undo_stack.append([serialize_component(c) for c in self._all])
        if len(self.undo_stack) > self.MAX_UNDO:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return
        snapshot = self.undo_stack.pop()
        ctx = self.window.ctx
        self._all.clear()
        self.selected_comps.clear()
        self.first_selected = None
        for cdata in snapshot:
            comp = create_component(ctx, cdata)
            if comp:
                self._all.append(comp)

    def load_layout(self):
        if os.path.exists(self.layout_file):
            try:
                with open(self.layout_file, 'r') as f:
                    self.components_data = json.load(f).get("components", [])
            except Exception as e:
                print(f"Error cargando layout: {e}")

    def save_layout(self):
        data = {"components": [serialize_component(c) for c in self._all]}
        try:
            with open(self.layout_file, 'w') as f:
                json.dump(data, f, indent=4)
            print("Layout guardado.")
        except Exception as e:
            print(f"Error guardando layout: {e}")

    def on_show_view(self):
        self._all.clear()
        ctx = self.window.ctx
        if not self.components_data:
            print("Generando layout base por defecto...")
            images = sorted(glob.glob("images/*.jpg"))
            d_img = images[0] if images else None
            
            cx_left, cx_right, cx_center = 140, ui.SW - 175, 280 + (ui.SW - 630)//2
            
            self._all.append(create_component(ctx, {"type":"ShaderButton","label":"Pausar/Menú","cx":cx_left,"cy":ui.SH-42,"w":210,"h":35}))
            self._all.append(create_component(ctx, {"type":"Avatar","cx":cx_left,"cy":ui.SH-154,"w":84}))
            self._all.append(create_component(ctx, {"type":"TextComponent","label":"4000 PV","cx":cx_left,"cy":ui.SH-224,"w":210,"font_size":22}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Mano: 4","cx":cx_left-56,"cy":ui.SH-266,"w":98,"h":25}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Cementerio: 6","cx":cx_left+56,"cy":ui.SH-266,"w":98,"h":25}))
            
            for i, ph in enumerate(["DP", "SP", "M1", "BP", "M2", "EP"]):
                c = create_component(ctx, {"type":"ShaderCircle","label":ph,"cx":cx_left-90+18 + i*36,"cy":ui.SH//2,"w":32})
                if ph == "BP":
                    c.fill, c.border = (40, 120, 200), (100, 200, 255)
                self._all.append(c)
                
            self._all.append(create_component(ctx, {"type":"Avatar","cx":cx_left,"cy":266,"w":84}))
            self._all.append(create_component(ctx, {"type":"TextComponent","label":"8000 PV","cx":cx_left,"cy":196,"w":210,"font_size":25}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Mano: 5","cx":cx_left-56,"cy":154,"w":98,"h":25}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Cementerio: 3","cx":cx_left+56,"cy":154,"w":98,"h":25}))
            self._all.append(create_component(ctx, {"type":"ShaderButton","label":"Fase Batalla","cx":cx_left,"cy":91,"w":210,"h":35}))
            self._all.append(create_component(ctx, {"type":"ShaderButton","label":"Pasar Turno","cx":cx_left,"cy":42,"w":210,"h":35}))
            
            self._all.append(create_component(ctx, {"type":"ShaderPanel","label":"Detalles de Carta","cx":cx_right,"cy":ui.SH-252,"w":308,"h":476}))
            c_cy = ui.SH-252 + 238 - 21 - 161
            self._all.append(create_component(ctx, {"type":"CardZone","cx":cx_right,"cy":c_cy,"w":224,"h":322, "image_path":d_img}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"A. AGUA","cx":cx_right-91,"cy":c_cy-179,"w":84,"h":21}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Lvl. 8","cx":cx_right,"cy":c_cy-179,"w":84,"h":21}))
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Aqua","cx":cx_right+91,"cy":c_cy-179,"w":84,"h":21}))
            
            self._all.append(create_component(ctx, {"type":"ShaderPanel","label":"Registro Duelo","cx":cx_right,"cy":112,"w":308,"h":182}))
            log="[Turno 1] Invocó Alien\\n[Batalla] PV: -1000\\n"
            self._all.append(create_component(ctx, {"type":"TextComponent","label":log,"cx":cx_right,"cy":112,"w":266,"font_size":10,"multiline":"True"}))
            
            self._all.append(create_component(ctx, {"type":"ShaderPill","label":"Filtros: Monstruo | Hechizo | Trampa","cx":cx_center,"cy":ui.SH-28,"w":420,"h":28}))
            
            self._all.append(create_component(ctx, {"type":"ShaderPanel","label":"Tablero Oponente","cx":cx_center,"cy":ui.SH//2+130,"w":cx_center*2-560-28,"h":240}))
            opp_m_y, slot_w, slot_h, gap = ui.SH//2+130 - 21, 95, 136, 10
            for i in range(5):
                self._all.append(create_component(ctx, {"type":"CardZone","cx":cx_center - 2*105 + i*105,"cy":opp_m_y,"w":slot_w,"h":slot_h,"image_path":d_img}))
                
            self._all.append(create_component(ctx, {"type":"ShaderPanel","label":"Tablero Jugador","cx":cx_center,"cy":ui.SH//2-130,"w":cx_center*2-560-28,"h":240}))
            ply_m_y = ui.SH//2-130 + 21
            for i in range(5):
                self._all.append(create_component(ctx, {"type":"CardZone","cx":cx_center - 2*105 + i*105,"cy":ply_m_y,"w":slot_w,"h":slot_h,"image_path":d_img}))
                
            self._all.append(create_component(ctx, {"type":"ShaderPanel","label":"","cx":cx_center,"cy":84,"w":cx_center*2-560-140,"h":140}))
            hx = cx_center - 4.5*80
            for i in range(10):
                self._all.append(create_component(ctx, {"type":"CardZone","cx":hx + i*80,"cy":84,"w":77,"h":112,"image_path":d_img}))
            
            for i, c in enumerate(self._all):
                c.z = i
            self.save_layout()
        else:
            for cdata in self.components_data:
                comp = create_component(ctx, cdata)
                if comp: self._all.append(comp)

    def spawn_component(self, ctype):
        self.push_undo()
        ctx = self.window.ctx
        data = {"type": ctype, "label": ctype, "cx": ui.SW//2, "cy": ui.SH//2, "w": 150, "h": 50}
        comp = create_component(ctx, data)
        if comp:
            comp.z = max((c.z for c in self._all), default=-1) + 1
            self._all.append(comp)
            self.selected_comps = {comp}
            if hasattr(comp, '_build_geo'): comp._build_geo()

    def get_comp_at(self, x, y):
        by_z = sorted(self._all, key=lambda c: getattr(c, 'z', 0), reverse=True)
        # Primero buscar entre los que NO son ShaderPanel para darles prioridad (hitboxes interiores)
        for c in by_z:
            if c.__class__.__name__ != "ShaderPanel":
                if hasattr(c, "contains") and c.contains(x, y): return c
                if hasattr(c, "w") and abs(c.cx - x) <= c.w/2 and abs(c.cy - y) <= getattr(c,'h',c.w)/2: return c
        # Luego paneles (backgrounds)
        for c in by_z:
            if c.__class__.__name__ == "ShaderPanel":
                if hasattr(c, "contains") and c.contains(x, y): return c
                if hasattr(c, "w") and abs(c.cx - x) <= c.w/2 and abs(c.cy - y) <= getattr(c,'h',c.w)/2: return c
        return None

    def get_comps_in_rect(self, x1, y1, x2, y2):
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        found = set()
        for c in self._all:
            if min_x <= c.cx <= max_x and min_y <= c.cy <= max_y:
                found.add(c)
        return found

    def on_mouse_press(self, x, y, button, modifiers):
        if self.f3_menu:
            menu_y = ui.SH // 2 + 100
            for ctype in ["ShaderButton", "ShaderPill", "ShaderPanel", "ShaderCircle", "CardZone", "TextComponent"]:
                if abs(x - ui.SW//2) < 100 and abs(y - menu_y) < 20:
                    self.spawn_component(ctype)
                    self.f3_menu = False
                    return
                menu_y -= 40
            self.f3_menu = False
            return

        selected_one = self.first_selected or (next(iter(self.selected_comps)) if self.selected_comps else None)
        if self.f4_menu and selected_one:
            cx_f4 = ui.SW - 150
            if abs(x - cx_f4) < 150 and abs(y - ui.SH//2) < 200:
                prop_y = ui.SH // 2 + 50
                props = ["label", "w", "h", "font_size", "multiline"]
                for p in props:
                    if abs(y - prop_y) < 20:
                        self.push_undo()
                        self.editing_prop = p
                        v = getattr(selected_one, p, getattr(selected_one, 'title', '') if p == 'label' else '')
                        if p == "font_size" and hasattr(selected_one, '_text_obj'): v = selected_one._text_obj.font_size
                        self.editing_text = str(v)
                        return
                    prop_y -= 40
                self.editing_prop = None
                return
            
        if self.edit_mode and button == arcade.MOUSE_BUTTON_LEFT:
            self.editing_prop = None

            # Ctrl+drag: marquee forzado sobre lo que haya debajo
            if modifiers & arcade.key.MOD_CTRL:
                self.selected_comps.clear()
                self.first_selected = None
                self.marquee_start = (x, y)
                self.marquee_end = (x, y)
                return

            # Check resize on single selection
            if len(self.selected_comps) == 1:
                c = next(iter(self.selected_comps))
                if hasattr(c, 'w'):
                    ch = getattr(c, 'h', c.w)
                    if abs(x - (c.cx + c.w/2)) < 20 and abs(y - (c.cy - ch/2)) < 20:
                        self.push_undo()
                        self.resizing_comp = c
                        return
            
            c = self.get_comp_at(x, y)
            if c:
                if modifiers & arcade.key.MOD_SHIFT:
                    if c in self.selected_comps:
                        self.selected_comps.remove(c)
                        if c == self.first_selected:
                            self.first_selected = next(iter(self.selected_comps), None)
                    else:
                        self.selected_comps.add(c)
                        if self.first_selected is None:
                            self.first_selected = c
                else:
                    if c not in self.selected_comps:
                        self.selected_comps = {c}
                        self.first_selected = c

                self.push_undo()
                self.drag_start_pos = (x, y)
                self.comp_start_positions = {comp: (comp.cx, comp.cy) for comp in self.selected_comps}
            else:
                if not (modifiers & arcade.key.MOD_SHIFT):
                    self.selected_comps.clear()
                    self.first_selected = None
                self.marquee_start = (x, y)
                self.marquee_end = (x, y)

    def on_mouse_release(self, x, y, button, modifiers):
        self.drag_start_pos = None
        self.resizing_comp = None
        if self.marquee_start and self.marquee_end:
            selection = self.get_comps_in_rect(self.marquee_start[0], self.marquee_start[1], self.marquee_end[0], self.marquee_end[1])
            if modifiers & arcade.key.MOD_SHIFT:
                self.selected_comps.update(selection)
            else:
                self.selected_comps = selection
                self.first_selected = next(iter(selection), None)
        self.marquee_start = None
        self.marquee_end = None

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.edit_mode and not self.f3_menu:
            if self.resizing_comp:
                c = self.resizing_comp
                ch = getattr(c, 'h', c.w)
                left = c.cx - c.w/2
                top = c.cy + ch/2
                new_w = max(20, x - left)
                new_h = max(20, top - y)
                c.w = new_w
                if hasattr(c, 'h'): c.h = new_h
                c.cx = left + new_w/2
                c.cy = top - new_h/2
                if hasattr(c, '_build_geo'): c._build_geo()
                if c.__class__.__name__ == "TextComponent" and c.multiline:
                    c._build_text(getattr(c, 'label', ''))
            elif self.drag_start_pos:
                dx_tot = x - self.drag_start_pos[0]
                dy_tot = y - self.drag_start_pos[1]
                for comp, (scx, scy) in self.comp_start_positions.items():
                    comp.cx = scx + dx_tot
                    comp.cy = scy + dy_tot
                    if hasattr(comp, '_build_geo'): comp._build_geo()
            elif self.marquee_start:
                self.marquee_end = (x, y)

    def apply_align(self, anchor):
        if not self.first_selected or not self.selected_comps:
            return
        ref = self.first_selected
        ref_h = getattr(ref, 'h', ref.w)
        self.push_undo()
        for c in self.selected_comps:
            ch = getattr(c, 'h', c.w)
            if self.align_mode == 'H':
                if anchor == 'top':
                    c.cy = (ref.cy + ref_h / 2) - ch / 2
                elif anchor == 'center':
                    c.cy = ref.cy
                elif anchor == 'bottom':
                    c.cy = (ref.cy - ref_h / 2) + ch / 2
            elif self.align_mode == 'V':
                if anchor == 'left':
                    c.cx = (ref.cx - ref.w / 2) + c.w / 2
                elif anchor == 'center':
                    c.cx = ref.cx
                elif anchor == 'right':
                    c.cx = (ref.cx + ref.w / 2) - c.w / 2
            if hasattr(c, '_build_geo'):
                c._build_geo()
        self.align_mode = None

    def apply_spacing(self):
        try:
            gap = float(self.spacing_text)
        except ValueError:
            return
        comps = list(self.selected_comps)
        if len(comps) < 2:
            return
        # Detectar eje dominante por el spread de centros
        xs = [c.cx for c in comps]
        ys = [c.cy for c in comps]
        if (max(xs) - min(xs)) >= (max(ys) - min(ys)):
            # Distribuir horizontalmente: ordenar por cx, anclar el primero
            comps.sort(key=lambda c: c.cx)
            cursor = comps[0].cx + comps[0].w / 2
            for c in comps[1:]:
                c.cx = cursor + gap + c.w / 2
                cursor = c.cx + c.w / 2
                if hasattr(c, '_build_geo'): c._build_geo()
        else:
            # Distribuir verticalmente: ordenar por cy desc (arriba primero), anclar el primero
            comps.sort(key=lambda c: c.cy, reverse=True)
            cursor = comps[0].cy - getattr(comps[0], 'h', comps[0].w) / 2
            for c in comps[1:]:
                ch = getattr(c, 'h', c.w)
                c.cy = cursor - gap - ch / 2
                cursor = c.cy - ch / 2
                if hasattr(c, '_build_geo'): c._build_geo()

    def apply_property(self):
        if not self.selected_comps or not self.editing_prop: return
        val = self.editing_text
        for c in self.selected_comps:
            if self.editing_prop == "id":
                c._id = val
            elif self.editing_prop == "label":
                if hasattr(c, "label"): c.label = val
                elif hasattr(c, "title"): c.title = val
                if hasattr(c, "_build_text"): c._build_text(val)
            elif self.editing_prop == "multiline" and c.__class__.__name__ == "TextComponent":
                c.multiline = val.lower() == "true"
                c._build_text(getattr(c, 'label', ''))
            elif self.editing_prop in ["w", "h", "font_size", "z"]:
                try:
                    v = float(val) if self.editing_prop in ["w", "h"] else int(val)
                    if self.editing_prop == "font_size" and hasattr(c, "_build_text"):
                        c.font_size = v
                        c._build_text(getattr(c, 'label', ''))
                    else:
                        setattr(c, self.editing_prop, v)
                        if hasattr(c, '_build_geo'): c._build_geo()
                except:
                    pass

    def on_key_press(self, symbol, mod):
        if self.align_mode:
            if symbol == arcade.key.ESCAPE:
                self.align_mode = None
            elif self.align_mode == 'H':
                if symbol == arcade.key.A:   self.apply_align('top')
                elif symbol == arcade.key.C: self.apply_align('center')
                elif symbol == arcade.key.B: self.apply_align('bottom')
            elif self.align_mode == 'V':
                if symbol == arcade.key.I:   self.apply_align('left')
                elif symbol == arcade.key.C: self.apply_align('center')
                elif symbol == arcade.key.D: self.apply_align('right')
            return

        if self.spacing_mode:
            if symbol == arcade.key.ENTER:
                self.push_undo()
                self.apply_spacing()
                self.spacing_mode = False
            elif symbol == arcade.key.ESCAPE:
                self.spacing_mode = False
            elif symbol == arcade.key.BACKSPACE:
                self.spacing_text = self.spacing_text[:-1]
            return

        if self.editing_prop:
            if symbol == arcade.key.ENTER:
                self.apply_property()
                self.editing_prop = None
            elif symbol == arcade.key.BACKSPACE:
                self.editing_text = self.editing_text[:-1]
                self.apply_property()
            return
            
        if self.edit_mode and symbol == arcade.key.DELETE:
            self.push_undo()
            for c in self.selected_comps:
                if c in self._all: self._all.remove(c)
            self.selected_comps.clear()
            self.first_selected = None
            self.f4_menu = False
            return

        if self.edit_mode and len(self.selected_comps) == 1:
            c = next(iter(self.selected_comps))
            if symbol == arcade.key.PAGEUP:
                self.push_undo()
                c.z += 1
                return
            elif symbol == arcade.key.PAGEDOWN:
                self.push_undo()
                c.z -= 1
                return

        if self.edit_mode and len(self.selected_comps) > 1 and self.first_selected:
            if symbol == arcade.key.H and mod & arcade.key.MOD_CTRL:
                self.align_mode = 'H'
                return
            elif symbol == arcade.key.V and mod & arcade.key.MOD_CTRL:
                self.align_mode = 'V'
                return
            elif symbol == arcade.key.S and mod & arcade.key.MOD_CTRL:
                self.spacing_mode = True
                return
            
        if self.edit_mode and symbol == arcade.key.Z and mod & arcade.key.MOD_CTRL:
            self.undo()
            return

        if symbol == arcade.key.ESCAPE:
            arcade.exit()
        elif symbol == arcade.key.F2:
            self.edit_mode = not self.edit_mode
            if not self.edit_mode:
                self.selected_comps.clear()
                self.f3_menu = False
                self.f4_menu = False
                self.save_layout()
        elif symbol == arcade.key.F3 and self.edit_mode:
            self.f3_menu = not self.f3_menu
        elif symbol == arcade.key.F4 and self.edit_mode:
            self.f4_menu = not self.f4_menu

    def on_text(self, text):
        if self.spacing_mode and (text.isdigit() or text == '.'):
            self.spacing_text += text
            return
        if self.editing_prop and text.isprintable():
            self.editing_text += text
            self.apply_property()

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, ui.SW, 0, ui.SH, ui.BG)
        for c in sorted(self._all, key=lambda c: getattr(c, 'z', 0)):
            if hasattr(c, 'draw'): c.draw()
            
        if self.edit_mode:
            arcade.draw_text("MODO EDICIÓN", 20, ui.SH - 30, arcade.color.YELLOW, font_size=20)
            arcade.draw_text("[F2] Guardar  [F3] Add  [F4] Props  [DEL] Borrar  [PgUp/PgDn] Z  [Shift] Multi  [Ctrl+H] Alinear H  [Ctrl+V] Alinear V  [Ctrl+S] Espaciado", 20, ui.SH - 60, arcade.color.YELLOW, font_size=14)
            
            for p in self.selected_comps:
                ch = getattr(p, 'h', p.w)
                left, right = p.cx - p.w/2, p.cx + p.w/2
                bottom, top = p.cy - ch/2, p.cy + ch/2
                arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.CYAN, 2)
                # Resize handle only when 1 item selected
                if len(self.selected_comps) == 1:
                    arcade.draw_lrbt_rectangle_filled(right - 15, right, bottom, bottom + 15, arcade.color.CYAN)
            
            if self.marquee_start and self.marquee_end:
                min_x, max_x = min(self.marquee_start[0], self.marquee_end[0]), max(self.marquee_start[0], self.marquee_end[0])
                min_y, max_y = min(self.marquee_start[1], self.marquee_end[1]), max(self.marquee_start[1], self.marquee_end[1])
                arcade.draw_lrbt_rectangle_outline(min_x, max_x, min_y, max_y, arcade.color.WHITE, 1)
                
        if self.align_mode:
            cx, cy = ui.SW // 2, ui.SH // 2
            arcade.draw_lrbt_rectangle_filled(cx - 180, cx + 180, cy - 80, cy + 80, (30, 30, 40, 240))
            arcade.draw_lrbt_rectangle_outline(cx - 180, cx + 180, cy - 80, cy + 80, arcade.color.CYAN, 1)
            if self.align_mode == 'H':
                arcade.draw_text("Alinear horizontal — eje Y", cx, cy + 50, arcade.color.WHITE, font_size=14, anchor_x="center")
                arcade.draw_text("[A] Arriba    [C] Centro    [B] Abajo", cx, cy + 10, arcade.color.YELLOW, font_size=13, anchor_x="center")
            else:
                arcade.draw_text("Alinear vertical — eje X", cx, cy + 50, arcade.color.WHITE, font_size=14, anchor_x="center")
                arcade.draw_text("[I] Izquierda    [C] Centro    [D] Derecha", cx, cy + 10, arcade.color.YELLOW, font_size=13, anchor_x="center")
            arcade.draw_text("[ESC] Cancelar", cx, cy - 40, (150, 150, 150), font_size=11, anchor_x="center")

        if self.spacing_mode:
            cx, cy = ui.SW // 2, ui.SH // 2
            arcade.draw_lrbt_rectangle_filled(cx - 160, cx + 160, cy - 50, cy + 50, (30, 30, 40, 240))
            arcade.draw_lrbt_rectangle_outline(cx - 160, cx + 160, cy - 50, cy + 50, arcade.color.CYAN, 1)
            arcade.draw_text("Espaciado (px):", cx, cy + 20, arcade.color.WHITE, font_size=14, anchor_x="center")
            arcade.draw_text(self.spacing_text + "|", cx, cy - 15, arcade.color.YELLOW, font_size=18, anchor_x="center")

        if self.f3_menu:
            arcade.draw_lrbt_rectangle_filled(ui.SW//2 - 150, ui.SW//2 + 150, ui.SH//2 - 200, ui.SH//2 + 200, (30,30,40, 230))
            arcade.draw_text("Añadir Componente", ui.SW//2, ui.SH//2 + 160, arcade.color.WHITE, font_size=18, anchor_x="center")
            menu_y = ui.SH // 2 + 100
            for ctype in ["ShaderButton", "ShaderPill", "ShaderPanel", "ShaderCircle", "CardZone", "TextComponent"]:
                arcade.draw_lrbt_rectangle_filled(ui.SW//2 - 100, ui.SW//2 + 100, menu_y - 15, menu_y + 15, (60,60,80))
                arcade.draw_text(ctype, ui.SW//2, menu_y, arcade.color.WHITE, anchor_x="center", anchor_y="center")
                menu_y -= 40

        if self.f4_menu and self.selected_comps:
            cx_f4 = ui.SW - 150
            arcade.draw_lrbt_rectangle_filled(cx_f4 - 150, cx_f4 + 150, ui.SH//2 - 200, ui.SH//2 + 200, (30,30,40, 230))
            
            selected_one = self.first_selected or next(iter(self.selected_comps))
            n = len(self.selected_comps)
            label_title = f"Props: {getattr(selected_one, '_type', 'Comp')}" + (f" (x{n})" if n > 1 else "")
            arcade.draw_text(label_title, cx_f4, ui.SH//2 + 160, arcade.color.WHITE, font_size=14, anchor_x="center")
            
            props = [
                ("id",    getattr(selected_one, "_id", "")),
                ("label", getattr(selected_one, "label", getattr(selected_one, "title", ""))),
                ("w",     str(selected_one.w)),
                ("h",     str(getattr(selected_one, 'h', ''))),
                ("z",     str(getattr(selected_one, "z", 0))),
            ]

            if selected_one.__class__.__name__ == "TextComponent":
                props.append(("multiline", str(getattr(selected_one, "multiline", False))))
                props.append(("font_size", str(getattr(selected_one, "font_size", 12))))
                
            prop_y = ui.SH // 2 + 50
            for pname, pval in props:
                color = arcade.color.YELLOW if self.editing_prop == pname else arcade.color.WHITE
                text_to_draw = self.editing_text if self.editing_prop == pname else pval
                arcade.draw_text(f"{pname}: {text_to_draw}", cx_f4 - 130, prop_y, color, font_size=12, anchor_y="center")
                prop_y -= 40

def main():
    win = arcade.Window(ui.SW, ui.SH, "YGO Duel Arena - Editor", fullscreen=False, samples=8)
    win.set_update_rate(1/60)
    win.show_view(BattleView())
    arcade.run()

if __name__ == "__main__":
    main()
