# game/game_engine.py
#
# GameEngine: el árbitro. Único responsable de modificar el GameState.
#
# Flujo general:
#   1. La interfaz llama un método request_* (request_normal_summon, request_attack, etc.)
#   2. El motor valida, luego setea state.pending_input con lo que necesita del jugador
#   3. La interfaz lee pending_input, muestra el prompt adecuado y llama provide_input(data)
#   4. El motor retoma, aplica la acción y puede pedir otro input o abrir prioridad
#
# Tipos de pending_input:
#   {"type": "priority",       "holder": int, "holder_name": str}
#   {"type": "select_tribute", "count": int,  "valid_zones": list[int]}
#   {"type": "select_zone",    "zone_type": "monster"|"spell_trap", "valid_zones": list[int]}
#   {"type": "select_target",  "context": str, "direct_available": bool, "valid_targets": list}
#   {"type": "acknowledge",    "message": str}

import random
from database import DatabaseManager
from game.game_card import GameCard
from game.deck import Deck
from game.enums import Phase, Position
from game.game_state import GameState
from game.player import Player

_EXTRA_DECK_TYPES = {"Fusion", "Synchro", "Xyz", "Link"}
_db = DatabaseManager()


class GameEngine:
    def __init__(self, player1: Player, player2: Player):
        self.state = GameState(player1, player2)
        self._pending_continuation = None   # callable(data) que retoma la acción pausada
        self._on_priority_closed   = None   # callable() que se ejecuta cuando ambos pasan sin cadena
        self._load_deck(player1)
        self._load_deck(player2)

    def _load_deck(self, player: Player):
        """Consulta la DB, construye GameCard y los asigna al mazo del jugador."""
        entries = _db.get_deck_cards(player.selected_deck)
        main, extra = [], []
        for entry in entries:
            for _ in range(entry['quantity']):
                card = GameCard(entry)
                subtypes = set(entry.get('type', '').split('/'))
                if subtypes & _EXTRA_DECK_TYPES:
                    extra.append(card)
                else:
                    main.append(card)
        random.shuffle(main)
        player.deck = Deck(main)
        player.extra_deck = Deck(extra)

    # ── Sistema de input pendiente ─────────────────────────────────────────────

    def _request_input(self, spec: dict, continuation):
        """Pausa el motor y le señala a la interfaz qué necesita.
        spec: descripción del input requerido (se escribe en state.pending_input)
        continuation: callable(data) que se llama cuando la interfaz provee la respuesta.
        """
        self.state.pending_input = spec
        self._pending_continuation = continuation

    def provide_input(self, data: dict):
        """La interfaz (texto o gráfica) llama esto con la respuesta del jugador.
        Limpia pending_input y ejecuta la continuación guardada.
        """
        if self.state.pending_input is None:
            raise ValueError("No hay input pendiente.")
        self.state.pending_input = None
        cont = self._pending_continuation
        self._pending_continuation = None
        cont(data)

    # ── Fases ─────────────────────────────────────────────────────────────────

    def advance_phase(self):
        """Avanza a la siguiente fase del turno."""
        _next = {
            Phase.DRAW:    Phase.STANDBY,
            Phase.STANDBY: Phase.MAIN1,
            Phase.MAIN1:   Phase.BATTLE,
            Phase.BATTLE:  Phase.MAIN2,
            Phase.MAIN2:   Phase.END,
        }
        if self.state.phase == Phase.END:
            self._end_turn()
        else:
            next_phase = _next[self.state.phase]
            # El primer jugador no puede atacar en el turno 1
            if next_phase == Phase.BATTLE and self.state.turn_number == 1:
                next_phase = Phase.MAIN2
                print("[Regla] El primer jugador no puede atacar en el turno 1. Pasando a Principal 2.")
            self.state.phase = next_phase
            print(f"[Fase] {self.state.phase.name}")
            self._open_priority_window()

    def _end_turn(self):
        """Cierra el turno activo y pasa el control al otro jugador."""
        for card in self.state.active_player.monster_zones:
            if card is not None:
                card.attacked_this_turn = False
                card.summoned_this_turn = False

        self.state.active_player_index = 1 - self.state.active_player_index
        self.state.turn_number += 1
        self.state.phase = Phase.DRAW
        self.state.normal_summon_used = False
        self.state.battle_phase_available = True

        print(f"[Turno {self.state.turn_number}] Turno de {self.state.active_player.name}.")
        self.draw(self.state.active_player_index, 1)
        self._open_priority_window()

    # ── Invocación normal — flujo multi-paso ──────────────────────────────────

    def request_normal_summon(self, card: GameCard, face_down: bool = False):
        """Inicia el flujo de invocación normal.
        Si el monstruo necesita tributos primero pide select_tribute,
        luego pide select_zone para elegir dónde colocarlo.
        """
        if not self.can_normal_summon(card):
            raise ValueError(f"No se puede invocar normalmente {card.name} ahora.")

        level = card.level or 0
        required = 0 if level <= 4 else (1 if level <= 6 else 2)

        if required > 0:
            valid_tributes = [i for i, c in enumerate(self.state.active_player.monster_zones) if c is not None]
            if len(valid_tributes) < required:
                raise ValueError(f"{card.name} requiere {required} tributo(s) pero no hay suficientes monstruos.")
            self._request_input(
                {"type": "select_tribute", "count": required, "valid_zones": valid_tributes},
                lambda data: self._after_tributes(card, required, face_down, data),
            )
        else:
            valid_zones = [i for i, c in enumerate(self.state.active_player.monster_zones) if c is None]
            self._request_input(
                {"type": "select_zone", "zone_type": "monster", "valid_zones": valid_zones},
                lambda data: self._after_summon_zone(card, [], face_down, data),
            )

    def _after_tributes(self, card, required, face_down, data):
        tribute_zones = data.get("zones", [])
        if len(tribute_zones) != required:
            raise ValueError(f"Se necesitan exactamente {required} zona(s) de tributo.")
        # Las zonas tributadas quedarán libres, contarlas como válidas para invocar
        valid_zones = [
            i for i, c in enumerate(self.state.active_player.monster_zones)
            if c is None or i in tribute_zones
        ]
        self._request_input(
            {"type": "select_zone", "zone_type": "monster", "valid_zones": valid_zones},
            lambda data: self._after_summon_zone(card, tribute_zones, face_down, data),
        )

    def _after_summon_zone(self, card, tribute_zones, face_down, data):
        zone_index = data.get("zone_index")
        if zone_index is None:
            raise ValueError("No se especificó zona de invocación.")
        self._normal_summon(card, zone_index, tribute_zones, face_down)

    def _normal_summon(self, card: GameCard, zone_index: int, tribute_zones: list[int], face_down: bool = False):
        """Ejecuta la invocación normal. Se llama solo cuando todos los datos ya fueron recolectados."""
        player = self.state.active_player

        for zone_i in tribute_zones:
            tribute = player.monster_zones[zone_i]
            if tribute is None:
                raise ValueError(f"La zona {zone_i} está vacía, no se puede tributar.")
            player.monster_zones[zone_i] = None
            self.send_to_graveyard(tribute)

        player.hand.remove(card)
        player.monster_zones[zone_index] = card
        card.zone = zone_index
        card.face_up = not face_down
        card.position = Position.DEFENSE if face_down else Position.ATTACK
        card.summoned_this_turn = True
        self.state.normal_summon_used = True
        print(f"[Invocación] {card.name} invocado por {player.name}.")
        self._open_priority_window()

    # ── Colocar magia/trampa — flujo multi-paso ───────────────────────────────

    def request_set(self, card: GameCard):
        """Inicia el flujo para colocar una magia o trampa boca abajo."""
        from game.enums import CardType
        if self.state.phase not in (Phase.MAIN1, Phase.MAIN2):
            raise ValueError("Solo podés colocar cartas en la Fase Principal.")
        if card.card_type not in (CardType.SPELL, CardType.TRAP):
            raise ValueError("Solo magias y trampas pueden colocarse boca abajo.")
        if card not in self.state.active_player.hand:
            raise ValueError(f"{card.name} no está en tu mano.")

        valid_zones = [i for i, c in enumerate(self.state.active_player.spell_trap_zones) if c is None]
        if not valid_zones:
            raise ValueError("No hay zonas de magia/trampa disponibles.")

        self._request_input(
            {"type": "select_zone", "zone_type": "spell_trap", "valid_zones": valid_zones},
            lambda data: self._after_set_zone(card, data),
        )

    def _after_set_zone(self, card, data):
        zone_index = data.get("zone_index")
        if zone_index is None:
            raise ValueError("No se especificó zona.")
        self._set_card(card, zone_index)

    def _set_card(self, card: GameCard, zone_index: int):
        """Coloca una magia o trampa boca abajo en la zona indicada."""
        player = self.state.active_player
        player.hand.remove(card)
        player.spell_trap_zones[zone_index] = card
        card.zone = zone_index
        card.face_up = False
        card.set_on_turn = self.state.turn_number
        print(f"[Set] {card.name} colocado boca abajo por {player.name}.")

    # ── Activar magia/trampa — flujo multi-paso ───────────────────────────────

    def request_activate(self, card: GameCard, effect_data: dict = None):
        """Inicia el flujo de activación de una magia o trampa.
        Si la carta viene de la mano primero pide select_zone, luego la activa.
        Si ya está en el campo (trampa boca abajo, continua) la activa directamente.
        """
        if not self.can_activate(card):
            raise ValueError(f"No se puede activar {card.name} ahora.")

        from game.enums import CardType
        player = self.state.active_player

        if card in player.hand and card.card_type == CardType.SPELL:
            valid_zones = [i for i, c in enumerate(player.spell_trap_zones) if c is None]
            if not valid_zones:
                raise ValueError("No hay zonas de magia/trampa disponibles.")
            self._request_input(
                {"type": "select_zone", "zone_type": "spell_trap", "valid_zones": valid_zones},
                lambda data: self._after_activate_zone(card, effect_data, data),
            )
        else:
            self._activate(card, effect_data)

    def _after_activate_zone(self, card, effect_data, data):
        zone_index = data.get("zone_index")
        if zone_index is None:
            raise ValueError("No se especificó zona.")
        player = self.state.active_player
        player.hand.remove(card)
        player.spell_trap_zones[zone_index] = card
        card.zone = zone_index
        self._activate(card, effect_data)

    def _activate(self, card: GameCard, data: dict = None):
        """Apila la carta en la cadena y pasa prioridad al oponente."""
        player = self.state.active_player
        controller_index = self.state.active_player_index

        card.face_up = True

        from game.effect import Effect
        effect = Effect(card, controller_index, data)
        self.state.chain.append(effect)
        self.state.chain_open = True

        self.state.consecutive_passes = 0
        self.state.priority_holder = 1 - controller_index
        next_holder = self.state.players[self.state.priority_holder]
        print(f"[Cadena {len(self.state.chain)}] {card.name} activado por {player.name}.")
        self._request_input(
            {"type": "priority", "holder": self.state.priority_holder, "holder_name": next_holder.name},
            self._handle_priority_response,
        )

    # ── Invocación especial ────────────────────────────────────────────────────

    def special_summon(self, card: GameCard, zone_index: int, reason: str):
        """Invocación especial. reason: 'effect' | 'inherent' | etc."""
        pass   # TODO

    # ── Ataque — flujo multi-paso ──────────────────────────────────────────────

    def request_attack(self, attacker: GameCard):
        """Inicia el flujo de declaración de ataque: pide seleccionar objetivo."""
        if self.state.phase != Phase.BATTLE:
            raise ValueError("Solo podés atacar en la Fase de Batalla.")
        if not attacker.face_up:
            raise ValueError("Un monstruo boca abajo no puede atacar.")
        if attacker.attacked_this_turn:
            raise ValueError(f"{attacker.name} ya atacó este turno.")
        if attacker not in self.state.active_player.monster_zones:
            raise ValueError(f"{attacker.name} no está en tu campo.")

        opponent_monsters = [c for c in self.state.inactive_player.monster_zones if c is not None]
        direct_available = len(opponent_monsters) == 0

        self._request_input(
            {
                "type": "select_target",
                "context": "attack",
                "direct_available": direct_available,
                "valid_targets": opponent_monsters,
            },
            lambda data: self._after_attack_target(attacker, data),
        )

    def _after_attack_target(self, attacker, data):
        target = data.get("target")   # GameCard o None para ataque directo
        self.declare_attack(attacker, target)

    def declare_attack(self, attacker: GameCard, target: GameCard | None):
        """Declara el ataque. Pasa prioridad al oponente para responder con trampas."""
        if not self.can_attack(attacker, target):
            raise ValueError(f"{attacker.name} no puede atacar ahora.")

        attacker.attacked_this_turn = True
        if target is None:
            print(f"[Batalla] {attacker.name} declara ataque directo.")
        else:
            print(f"[Batalla] {attacker.name} ataca a {target.name}.")

        self._open_priority_window(
            holder_index=1 - self.state.active_player_index,
            on_both_pass=lambda: self.execute_battle(attacker, target),
        )

    def execute_battle(self, attacker: GameCard, target: GameCard | None):
        """Ejecuta el paso de daño. Llamar después de que ambos jugadores pasen prioridad."""
        inactive = self.state.inactive_player
        if target is None:
            inactive.lp -= attacker.atk or 0
            print(f"[Daño] {inactive.name} recibe {attacker.atk}. LP: {inactive.lp}")
        else:
            self._resolve_battle(attacker, target)
        self._check_win_condition()

    def _resolve_battle(self, attacker: GameCard, target: GameCard):
        """Resuelve el combate entre dos monstruos."""
        atk_a = attacker.atk or 0
        if target.position == Position.ATTACK:
            atk_b = target.atk or 0
            if atk_a > atk_b:
                self.state.inactive_player.lp -= (atk_a - atk_b)
                self.send_to_graveyard(target)
                print(f"[Batalla] {target.name} destruido. LP oponente: {self.state.inactive_player.lp}")
            elif atk_a < atk_b:
                self.state.active_player.lp -= (atk_b - atk_a)
                self.send_to_graveyard(attacker)
                print(f"[Batalla] {attacker.name} destruido. LP jugador: {self.state.active_player.lp}")
            else:
                self.send_to_graveyard(attacker)
                self.send_to_graveyard(target)
                print(f"[Batalla] Empate. Ambos destruidos.")
        elif target.position in (Position.DEFENSE, Position.SET):
            def_b = target.def_ or 0
            if not target.face_up:
                target.face_up = True
                print(f"[Batalla] {target.name} revelado.")
            if atk_a > def_b:
                self.send_to_graveyard(target)
                print(f"[Batalla] {target.name} destruido.")
            elif atk_a < def_b:
                self.state.active_player.lp -= (def_b - atk_a)
                print(f"[Batalla] Daño de penetración: {def_b - atk_a}. LP: {self.state.active_player.lp}")
            else:
                print(f"[Batalla] Empate en defensa. Nadie destruido.")

    def can_attack(self, attacker: GameCard, target: GameCard | None) -> bool:
        if self.state.phase != Phase.BATTLE:
            return False
        if not attacker.face_up:
            return False
        if attacker.attacked_this_turn:
            return False
        if attacker not in self.state.active_player.monster_zones:
            return False
        if target is None:
            return all(z is None for z in self.state.inactive_player.monster_zones)
        if target not in self.state.inactive_player.monster_zones:
            return False
        return True

    # ── Prioridad y cadenas ────────────────────────────────────────────────────

    def _has_activatable(self, player_index: int) -> bool:
        """Devuelve True si el jugador tiene al menos una carta que puede activar ahora."""
        player = self.state.players[player_index]
        for card in player.hand:
            if self.can_activate(card):
                return True
        for card in player.spell_trap_zones:
            if card is not None and self.can_activate(card):
                return True
        return False

    def _open_priority_window(self, holder_index: int = None, on_both_pass=None):
        """Abre una ventana de prioridad y pide input al jugador correspondiente.
        Si el jugador no tiene nada activable, pasa automáticamente.
        on_both_pass: callable() opcional que se ejecuta cuando ambos pasan sin cadena.
        """
        self._on_priority_closed = on_both_pass
        self.state.priority_window_open = True
        self.state.priority_holder = holder_index if holder_index is not None else self.state.active_player_index
        self.state.consecutive_passes = 0
        holder_i = self.state.priority_holder

        if not self._has_activatable(holder_i):
            # Auto-pasa sin preguntar, pasa al otro jugador
            self.state.consecutive_passes += 1
            other_i = 1 - holder_i
            if not self._has_activatable(other_i):
                # Ambos sin nada: cerrar ventana directamente
                self.state.consecutive_passes = 0
                self.state.priority_window_open = False
                if self.state.chain:
                    self.resolve_chain()
                elif self._on_priority_closed:
                    cb = self._on_priority_closed
                    self._on_priority_closed = None
                    cb()
                return
            # Solo el otro tiene algo: pedirle input
            self.state.priority_holder = other_i
            holder = self.state.players[other_i]
            print(f"[Prioridad] {holder.name}, ¿querés activar algo?")
            self._request_input(
                {"type": "priority", "holder": other_i, "holder_name": holder.name},
                self._handle_priority_response,
            )
            return

        holder = self.state.players[holder_i]
        print(f"[Prioridad] {holder.name}, ¿querés activar algo?")
        self._request_input(
            {"type": "priority", "holder": holder_i, "holder_name": holder.name},
            self._handle_priority_response,
        )

    def _handle_priority_response(self, data):
        action = data.get("action")
        if action == "pass":
            self._pass_priority()
        elif action == "activate":
            card = data.get("card")
            effect_data = data.get("effect_data")
            if card is None:
                raise ValueError("Se necesita especificar la carta a activar.")
            self.request_activate(card, effect_data)
        else:
            raise ValueError(f"Acción de prioridad desconocida: '{action}'. Usá 'pass' o 'activate'.")

    def _pass_priority(self):
        """El jugador con prioridad pasa. Si ambos pasaron, cierra la ventana y resuelve la cadena."""
        if not self.state.priority_window_open:
            raise ValueError("No hay ventana de prioridad abierta.")

        holder = self.state.players[self.state.priority_holder]
        print(f"[Prioridad] {holder.name} pasa.")
        self.state.consecutive_passes += 1

        if self.state.consecutive_passes >= 2:
            self.state.priority_window_open = False
            self.state.consecutive_passes = 0
            if self.state.chain:
                self.resolve_chain()
            elif self._on_priority_closed:
                cb = self._on_priority_closed
                self._on_priority_closed = None
                cb()
            return

        # Pasa al otro jugador
        self.state.priority_holder = 1 - self.state.priority_holder
        next_i = self.state.priority_holder

        if not self._has_activatable(next_i):
            # El siguiente tampoco tiene nada: auto-pasa y cierra
            self.state.consecutive_passes += 1
            self.state.priority_window_open = False
            self.state.consecutive_passes = 0
            if self.state.chain:
                self.resolve_chain()
            elif self._on_priority_closed:
                cb = self._on_priority_closed
                self._on_priority_closed = None
                cb()
            return

        next_holder = self.state.players[next_i]
        print(f"[Prioridad] {next_holder.name}, ¿querés activar algo?")
        self._request_input(
            {"type": "priority", "holder": next_i, "holder_name": next_holder.name},
            self._handle_priority_response,
        )

    def resolve_chain(self):
        """Resuelve la cadena actual en orden inverso (LIFO)."""
        from game.effects import EFFECT_REGISTRY
        self.state.chain_open = False
        while self.state.chain:
            effect = self.state.chain.pop()
            print(f"[Resolviendo] {effect}")
            for key in effect.source_card.effect_keys:
                effect_class = EFFECT_REGISTRY.get(key)
                if effect_class:
                    effect_class(effect.source_card, effect.controller_index, effect.data).resolve(self)
                else:
                    print(f"  [!] Efecto '{key}' no implementado todavía.")
            self._post_resolve(effect.source_card)

    def _post_resolve(self, card: GameCard):
        """Envía al cementerio las magias Normal y Quick-Play después de resolver."""
        from game.enums import CardType
        if card.card_type != CardType.SPELL:
            return
        if card.subtype in ("Normal", "Quick-Play", "Ritual"):
            self.send_to_graveyard(card)

    # ── Movimiento de cartas ───────────────────────────────────────────────────

    def send_to_graveyard(self, card: GameCard):
        """Envía una carta al cementerio desde donde esté."""
        owner = self._find_owner(card)
        self._remove_from_field(card)
        card.zone = None
        card.face_up = True
        owner.graveyard.append(card)

    def banish(self, card: GameCard):
        """Desvanece una carta (la saca del juego)."""
        owner = self._find_owner(card)
        self._remove_from_field(card)
        card.zone = None
        card.face_up = True
        owner.banished.append(card)

    def draw(self, player_index: int, count: int = 1):
        """Roba count cartas del deck y las agrega a la mano del jugador."""
        player = self.state.players[player_index]
        for _ in range(count):
            card = player.deck.draw()
            player.hand.append(card)

    def _find_owner(self, card: GameCard):
        for player in self.state.players:
            if (card in player.hand
                    or card in player.monster_zones
                    or card in player.spell_trap_zones
                    or card == player.field_zone
                    or card in player.graveyard
                    or card in player.banished):
                return player
        raise ValueError(f"No se encontró propietario para {card.name}.")

    def _remove_from_field(self, card: GameCard):
        for player in self.state.players:
            if card in player.hand:
                player.hand.remove(card)
                return
            for i, c in enumerate(player.monster_zones):
                if c is card:
                    player.monster_zones[i] = None
                    return
            for i, c in enumerate(player.spell_trap_zones):
                if c is card:
                    player.spell_trap_zones[i] = None
                    return
            if player.field_zone is card:
                player.field_zone = None
                return

    # ── Validaciones ──────────────────────────────────────────────────────────

    def can_normal_summon(self, card: GameCard) -> bool:
        from game.enums import CardType
        if self.state.phase not in (Phase.MAIN1, Phase.MAIN2):
            return False
        if self.state.normal_summon_used:
            return False
        if card.card_type != CardType.MONSTER:
            return False
        if card not in self.state.active_player.hand:
            return False
        return True

    def can_activate(self, card: GameCard) -> bool:
        from game.enums import CardType
        player = self.state.active_player
        if card.card_type == CardType.SPELL:
            if self.state.phase not in (Phase.MAIN1, Phase.MAIN2):
                return False
            if card not in player.hand and card not in player.spell_trap_zones:
                return False
        elif card.card_type == CardType.TRAP:
            if card.set_on_turn is None or card.set_on_turn >= self.state.turn_number:
                return False
            if card not in player.spell_trap_zones:
                return False
        else:
            return False
        return True

    def check_win_condition(self) -> str | None:
        return self._check_win_condition()

    def _check_win_condition(self) -> str | None:
        for player in self.state.players:
            if player.lp <= 0:
                winner = next(p for p in self.state.players if p is not player)
                print(f"[FIN] {winner.name} gana. {player.name} quedó sin LP.")
                return winner.name
            if player.deck.is_empty():
                winner = next(p for p in self.state.players if p is not player)
                print(f"[FIN] {winner.name} gana. {player.name} no puede robar.")
                return winner.name
        return None
