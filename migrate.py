"""
Migración one-time: DB vieja (tabla cards flat) → nuevo schema con herencia de tablas.
Preserva los mazos guardados. Hace backup de la DB original.

Uso: python migrate.py
"""
import os
import shutil
import sqlite3

DB_FILE = 'yugioh.db'
BACKUP_FILE = 'yugioh.db.bak'


def main():
    if not os.path.exists(DB_FILE):
        print('[migrate] No se encontró yugioh.db — nada que migrar.')
        return

    # Verificar si ya está migrado (columna card_type existe en cards)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'card_type' in columns:
        print('[migrate] La base de datos ya tiene el nuevo esquema. Nada que hacer.')
        conn.close()
        return

    print('[migrate] Leyendo datos existentes...')

    # Leer cartas viejas
    cursor.execute("SELECT * FROM cards")
    col_names = [desc[0] for desc in cursor.description]
    old_cards = [dict(zip(col_names, row)) for row in cursor.fetchall()]
    print(f'[migrate]   {len(old_cards)} cartas encontradas.')

    # Leer mazos
    cursor.execute("SELECT id, name, created_at FROM saved_decks")
    old_decks = cursor.fetchall()
    print(f'[migrate]   {len(old_decks)} mazos encontrados.')

    # Leer entradas de mazos
    cursor.execute("SELECT deck_id, card_cid, quantity FROM deck_entries")
    old_entries = cursor.fetchall()
    print(f'[migrate]   {len(old_entries)} entradas de mazo encontradas.')

    conn.close()

    # Backup
    shutil.copy2(DB_FILE, BACKUP_FILE)
    print(f'[migrate] Backup guardado en {BACKUP_FILE}')

    # Eliminar DB vieja y crear nueva con nuevo schema
    os.remove(DB_FILE)

    from database import DatabaseManager, MonsterCard, SpellCard, TrapCard, SavedDeck, DeckEntry
    from database import _parse_level, _parse_stat, _parse_subtype

    db = DatabaseManager(DB_FILE)
    print('[migrate] Nuevo schema creado.')

    # Reinsertar cartas con parsing correcto
    print('[migrate] Migrando cartas...')
    with db.Session() as session:
        for data in old_cards:
            cid  = data.get('cid', '')
            attr = data.get('attribute', '')
            if not cid:
                continue

            base_args = dict(
                cid        = cid,
                name       = data.get('name', ''),
                text       = data.get('text', ''),
                image_name = data.get('image_name', ''),
                image_url  = data.get('image_url', ''),
            )

            if attr == 'SPELL':
                card = SpellCard(
                    **base_args,
                    card_type = 'SPELL',
                    subtype   = _parse_subtype(data.get('type', '')),
                )
            elif attr == 'TRAP':
                card = TrapCard(
                    **base_args,
                    card_type = 'TRAP',
                    subtype   = _parse_subtype(data.get('type', '')),
                )
            else:
                card = MonsterCard(
                    **base_args,
                    card_type = 'MONSTER',
                    attribute = attr,
                    subtype   = _parse_subtype(data.get('type', '')),
                    level     = _parse_level(data.get('level', '')),
                    atk       = _parse_stat(data.get('atk')),
                    def_      = _parse_stat(data.get('def')),
                )
            session.merge(card)

        session.commit()
    print(f'[migrate]   {len(old_cards)} cartas migradas.')

    # También sincronizar desde JSONs por si hay cartas nuevas
    db.init_db()

    # Restaurar mazos
    if old_decks:
        print('[migrate] Restaurando mazos...')
        with db.Session() as session:
            deck_id_map = {}
            for old_id, name, created_at in old_decks:
                deck = SavedDeck(name=name, created_at=created_at)
                session.add(deck)
                session.flush()
                deck_id_map[old_id] = deck.id

            for old_deck_id, card_cid, quantity in old_entries:
                new_deck_id = deck_id_map.get(old_deck_id)
                if new_deck_id and card_cid:
                    entry = DeckEntry(deck_id=new_deck_id, card_cid=card_cid, quantity=quantity)
                    session.add(entry)

            session.commit()
        print(f'[migrate]   {len(old_decks)} mazos restaurados.')

    print('[migrate] ¡Migración completada!')
    print(f'[migrate] Backup disponible en {BACKUP_FILE} si algo salió mal.')


if __name__ == '__main__':
    main()
