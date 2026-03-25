#!/usr/bin/env python3
# yugi_text.py — Interfaz de texto para el motor YGO
#
# Uso:
#   python yugi_text.py
#
# Desde la consola podés manejar los dos jugadores en la misma sesión.
# Cuando la prioridad o el turno pasan al otro jugador, el script te avisa
# y podés escribir 'sw' para cambiar la perspectiva (oculta la mano del otro).

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import DatabaseManager
from game.game_engine import GameEngine
from game.game_card import GameCard
from game.player import Player
from game.enums import Phase, CardType

# ── ANSI ──────────────────────────────────────────────────────────────────────
R    = "\033[91m"
B    = "\033[94m"
Y    = "\033[93m"
G    = "\033[92m"
DIM  = "\033[2m"
BOLD = "\033[1m"
RST  = "\033[0m"

_db = DatabaseManager()

# ── Selección de decks ────────────────────────────────────────────────────────

def select_deck(player_name: str) -> dict:
    decks = _db.get_all_decks()
    if not decks:
        print("No hay decks guardados. Creá uno desde el deck builder primero.")
        sys.exit(1)
    print(f"\n{BOLD}── Deck para {player_name} ──{RST}")
    for i, d in enumerate(decks):
        print(f"  [{i+1}] {d['name']}")
    while True:
        raw = input(f"Opción (1-{len(decks)}): ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(decks):
                return decks[idx]
        except ValueError:
            pass
        print("  Opción inválida.")

# ── Display ───────────────────────────────────────────────────────────────────

_PHASE_LABEL = {
    Phase.DRAW:    "Robo",
    Phase.STANDBY: "Reserva",
    Phase.MAIN1:   "Principal 1",
    Phase.BATTLE:  "Batalla",
    Phase.MAIN2:   "Principal 2",
    Phase.END:     "Fin",
}

def _fmt_zones(zones, hide_facedown=False) -> str:
    parts = []
    for i, card in enumerate(zones):
        if card is None:
            parts.append(f"[{i}]···")
        elif not card.face_up and hide_facedown:
            parts.append(f"[{i}]???")
        else:
            pos = card.position.name[0]   # A / D / S
            parts.append(f"[{i}]{card.name[:10]}({pos})")
    return "  ".join(parts)

def show_board(engine: GameEngine, perspective: int):
    s   = engine.state
    me  = s.players[perspective]
    opp = s.players[1 - perspective]
    am  = "▶" if s.active_player_index == perspective else " "
    ao  = "▶" if s.active_player_index != perspective else " "

    print(f"\n{'─'*64}")
    print(f" Turno {s.turn_number}  │  {_PHASE_LABEL[s.phase]}  │  Activo: {s.active_player.name}")
    print(f"{'─'*64}")
    print(f"{ao} {R}{opp.name}{RST}  LP:{opp.lp}  Deck:{len(opp.deck)}  Mano:{len(opp.hand)}  Ceq:{len(opp.graveyard)}")
    print(f"     M/T : {_fmt_zones(opp.spell_trap_zones, hide_facedown=True)}")
    print(f"     MON : {_fmt_zones(opp.monster_zones,    hide_facedown=True)}")
    print(f"{'·'*64}")
    print(f"     MON : {_fmt_zones(me.monster_zones)}")
    print(f"     M/T : {_fmt_zones(me.spell_trap_zones)}")
    print(f"{am} {B}{me.name}{RST}  LP:{me.lp}  Deck:{len(me.deck)}  Mano:{len(me.hand)}  Ceq:{len(me.graveyard)}")
    if s.chain:
        print(f"  {Y}Cadena: {[str(e) for e in s.chain]}{RST}")
    print(f"{'─'*64}")

def show_hand(engine: GameEngine, player_index: int):
    player = engine.state.players[player_index]
    hand   = player.hand
    print(f"\n{BOLD}Mano de {player.name}:{RST}")
    if not hand:
        print("  (vacía)")
        return
    for i, card in enumerate(hand):
        extra = ""
        if card.card_type == CardType.MONSTER:
            extra = f"  Nv:{card.level}  ATK:{card.atk}  DEF:{card.def_}"
        print(f"  [{i}] {card.name}  ({card.card_type.name}){extra}")

def show_graveyard(engine: GameEngine, player_index: int):
    gy = engine.state.players[player_index].graveyard
    name = engine.state.players[player_index].name
    print(f"\n{BOLD}Cementerio de {name}:{RST}")
    if not gy:
        print("  (vacío)")
        return
    for i, card in enumerate(gy):
        print(f"  [{i}] {card.name}")

# ── Manejadores de pending_input ──────────────────────────────────────────────

def handle_pending(engine: GameEngine, perspective: int):
    """Despacha el pending_input al manejador correspondiente."""
    pi = engine.state.pending_input
    t  = pi["type"]

    if t == "priority":
        _handle_priority(engine, pi, perspective)
    elif t == "select_tribute":
        _handle_select_tribute(engine, pi)
    elif t == "select_zone":
        _handle_select_zone(engine, pi)
    elif t == "select_target":
        _handle_select_target(engine, pi)
    elif t == "acknowledge":
        input(f"  ► {pi['message']}  [Enter]")
        engine.provide_input({})
    else:
        print(f"[!] Tipo de input desconocido: {t}")


def _handle_priority(engine: GameEngine, pi: dict, perspective: int):
    holder_i = pi["holder"]
    holder   = engine.state.players[holder_i]
    s        = engine.state

    print(f"\n{Y}[Prioridad] {holder.name} — ¿activás algo?{RST}")

    # Cartas activables del holder (mano + campo)
    activables = []
    for i, card in enumerate(holder.hand):
        if card.card_type in (CardType.SPELL, CardType.TRAP) and engine.can_activate(card):
            activables.append(("mano", i, card))
    for i, card in enumerate(holder.spell_trap_zones):
        if card is not None and engine.can_activate(card):
            activables.append(("campo", i, card))

    print("  [p] Pasar")
    if activables:
        print("  Activables:")
        for j, (origen, i, card) in enumerate(activables):
            print(f"    [a{j}] {card.name}  (en {origen} zona {i})")

    while True:
        raw = input("  > ").strip().lower()
        if raw == "p":
            engine.provide_input({"action": "pass"})
            return
        if raw.startswith("a") and raw[1:].isdigit():
            j = int(raw[1:])
            if 0 <= j < len(activables):
                _, _, card = activables[j]
                engine.provide_input({"action": "activate", "card": card})
                return
        print("  Opción inválida. Usá 'p' para pasar o 'a0', 'a1'... para activar.")


def _handle_select_tribute(engine: GameEngine, pi: dict):
    count  = pi["count"]
    valid  = pi["valid_zones"]
    player = engine.state.active_player

    print(f"\n{Y}Elegí {count} monstruo(s) para tributar:{RST}")
    for i in valid:
        card = player.monster_zones[i]
        print(f"  [{i}] {card.name}  ATK:{card.atk}  DEF:{card.def_}")

    while True:
        raw = input(f"  {count} número(s) separados por espacio: ").strip()
        try:
            zones = [int(x) for x in raw.split()]
            if (len(zones) == count
                    and all(z in valid for z in zones)
                    and len(set(zones)) == count):
                engine.provide_input({"zones": zones})
                return
        except ValueError:
            pass
        print(f"  Necesitás exactamente {count} zona(s) válidas sin repetir.")


def _handle_select_zone(engine: GameEngine, pi: dict):
    valid     = pi["valid_zones"]
    zone_type = pi.get("zone_type", "")
    label     = "monstruo" if zone_type == "monster" else "magia/trampa"

    print(f"\n{Y}Elegí una zona de {label}. Disponibles: {valid}{RST}")
    while True:
        raw = input("  Número de zona: ").strip()
        try:
            z = int(raw)
            if z in valid:
                engine.provide_input({"zone_index": z})
                return
        except ValueError:
            pass
        print(f"  Zona inválida. Elegí una de: {valid}")


def _handle_select_target(engine: GameEngine, pi: dict):
    targets = pi["valid_targets"]
    direct  = pi.get("direct_available", False)

    print(f"\n{Y}Elegí objetivo de ataque:{RST}")
    if direct:
        print("  [d] Ataque directo al jugador")
    for i, card in enumerate(targets):
        face = card.position.name
        print(f"  [{i}] {card.name}  ATK:{card.atk}  DEF:{card.def_}  {face}")

    while True:
        raw = input("  > ").strip().lower()
        if raw == "d" and direct:
            engine.provide_input({"target": None})
            return
        try:
            idx = int(raw)
            if 0 <= idx < len(targets):
                engine.provide_input({"target": targets[idx]})
                return
        except ValueError:
            pass
        print("  Opción inválida.")

# ── Acciones del jugador activo ───────────────────────────────────────────────

_HELP = f"""
  {BOLD}Acciones:{RST}
  [s]       Ver tablero
  [h]       Ver mano
  [g N]     Ver cementerio (0=yo, 1=oponente)
  [v N]     Invocar carta N de la mano (Normal)
  [c N]     Colocar carta N boca abajo (Set)
  [a N]     Activar carta N de la mano
  [ac N]    Activar carta en zona de campo N
  [k N]     Atacar con monstruo en zona N
  [p]       Avanzar fase
  [sw]      Cambiar perspectiva (cambiar jugador)
  [q]       Salir
"""

def do_action(engine: GameEngine, perspective: int) -> int:
    """Ejecuta la acción elegida. Retorna la perspectiva activa (puede cambiar con sw)."""
    s      = engine.state
    player = s.active_player

    raw = input(f"\n{B}{player.name}{RST} [{_PHASE_LABEL[s.phase]}] > ").strip().lower()

    if raw == "s":
        show_board(engine, perspective)

    elif raw == "h":
        show_hand(engine, s.active_player_index)

    elif raw.startswith("g"):
        parts = raw.split()
        idx   = int(parts[1]) if len(parts) > 1 else 0
        show_graveyard(engine, idx % 2)

    elif raw.startswith("v "):
        try:
            idx  = int(raw[2:])
            card = player.hand[idx]
            engine.request_normal_summon(card)
        except (IndexError, ValueError) as e:
            print(f"  Error: {e}")

    elif raw.startswith("c "):
        try:
            idx  = int(raw[2:])
            card = player.hand[idx]
            engine.request_set(card)
        except (IndexError, ValueError) as e:
            print(f"  Error: {e}")

    elif raw.startswith("ac "):
        try:
            z    = int(raw[3:])
            card = player.spell_trap_zones[z]
            if card is None:
                print("  Zona vacía.")
            else:
                engine.request_activate(card)
        except (IndexError, ValueError) as e:
            print(f"  Error: {e}")

    elif raw.startswith("a "):
        try:
            idx  = int(raw[2:])
            card = player.hand[idx]
            engine.request_activate(card)
        except (IndexError, ValueError) as e:
            print(f"  Error: {e}")

    elif raw.startswith("k "):
        try:
            z    = int(raw[2:])
            card = player.monster_zones[z]
            if card is None:
                print("  Zona vacía.")
            else:
                engine.request_attack(card)
        except (IndexError, ValueError) as e:
            print(f"  Error: {e}")

    elif raw == "p":
        engine.advance_phase()

    elif raw == "sw":
        perspective = 1 - perspective
        show_board(engine, perspective)

    elif raw in ("?", "help"):
        print(_HELP)

    elif raw == "q":
        print("Saliendo...")
        sys.exit(0)

    else:
        print("  Comando desconocido. Escribí '?' para ver los comandos.")

    return perspective

# ── Loop principal ────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'═'*40}")
    print("   YGO Text Interface")
    print(f"{'═'*40}{RST}\n")

    deck1 = select_deck("Jugador 1")
    deck2 = select_deck("Jugador 2")

    p1 = Player("Jugador 1", deck1['id'])
    p2 = Player("Jugador 2", deck2['id'])

    engine = GameEngine(p1, p2)

    # Robo inicial: 5 cartas por jugador
    engine.draw(0, 5)
    engine.draw(1, 5)
    # El primer turno arranca en Main 1 (sin robo ni reserva)
    engine.state.phase = Phase.MAIN1

    perspective = 0   # índice del jugador "frente a la consola"

    print(f"\n{G}¡Duelo iniciado!{RST}")
    print(f"  Jugador 1: {deck1['name']}")
    print(f"  Jugador 2: {deck2['name']}")
    print(f"  Escribí '?' para ver los comandos.")
    show_board(engine, perspective)

    while True:
        s = engine.state

        # Condición de victoria
        winner = engine.check_win_condition()
        if winner:
            print(f"\n{G}{BOLD}¡{winner} gana el duelo!{RST}\n")
            break

        # ── Hay input pendiente ──
        if s.pending_input is not None:
            pi = s.pending_input

            # Si la prioridad la tiene el otro jugador, avisar
            if pi["type"] == "priority" and pi["holder"] != perspective:
                holder_name = s.players[pi["holder"]].name
                print(f"\n{Y}  ↳ Le toca responder a {holder_name}. Escribí 'sw' para cambiar.{RST}")
                raw = input("  > ").strip().lower()
                if raw == "sw":
                    perspective = pi["holder"]
                    show_board(engine, perspective)
                # Si no escribe 'sw', igual le mostramos el prompt de prioridad
                # en la próxima iteración con la perspectiva actual.

            handle_pending(engine, perspective)
            continue

        # ── Sin input pendiente: turno libre ──
        if s.active_player_index != perspective:
            # Le avisamos que es el turno del otro jugador
            print(f"\n{Y}  Es el turno de {s.active_player.name}. Escribí 'sw' para cambiar.{RST}")
            raw = input("  > ").strip().lower()
            if raw == "sw":
                perspective = s.active_player_index
                show_board(engine, perspective)
            elif raw == "q":
                sys.exit(0)
            continue

        perspective = do_action(engine, perspective)


if __name__ == "__main__":
    main()
