import os
import glob
import json
import re
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_level(raw: str) -> int | None:
    """'Level 4' → 4, '' → None"""
    if not raw:
        return None
    try:
        return int(raw.strip().split()[-1])
    except (ValueError, IndexError):
        return None


def _parse_stat(raw) -> int | None:
    """'1500' → 1500, '?' or '-' or None → None"""
    if raw is None or str(raw).strip() in ('', '?', '-'):
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def _parse_subtype(raw: str) -> str:
    """'[ Beast／Effect]' → 'Beast/Effect'"""
    if not raw:
        return ''
    cleaned = re.sub(r'[／]', '/', raw)
    cleaned = re.sub(r'[\[\]]', '', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip().strip('/')


# ── Models ────────────────────────────────────────────────────────────────────

class Card(Base):
    __tablename__ = 'cards'

    cid       = Column(String, primary_key=True)
    name      = Column(String, nullable=False)
    text      = Column(String)
    image_name = Column(String)
    image_url  = Column(String)
    card_type  = Column(String, nullable=False)  # 'MONSTER' | 'SPELL' | 'TRAP'

    __mapper_args__ = {
        'polymorphic_on': card_type,
        'polymorphic_identity': 'CARD',
    }

    def to_dict(self):
        return {
            'cid':        self.cid,
            'name':       self.name,
            'text':       self.text,
            'image_name': self.image_name,
            'image_url':  self.image_url,
            'card_type':  self.card_type,
        }


class MonsterCard(Card):
    __tablename__ = 'monster_cards'

    cid       = Column(String, ForeignKey('cards.cid'), primary_key=True)
    attribute = Column(String)   # DARK, LIGHT, FIRE, etc.
    subtype   = Column(String)   # 'Spellcaster/Effect', 'Dragon/Normal', etc.
    level     = Column(Integer)  # NULL for Link monsters
    atk       = Column(Integer)  # NULL for '?' ATK
    def_      = Column('def', Integer)  # NULL for Link or '?' DEF

    __mapper_args__ = {'polymorphic_identity': 'MONSTER'}

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'attribute': self.attribute,
            'type':      self.subtype,
            'level':     self.level,
            'atk':       self.atk,
            'def':       self.def_,
        })
        return d


class SpellCard(Card):
    __tablename__ = 'spell_cards'

    cid     = Column(String, ForeignKey('cards.cid'), primary_key=True)
    subtype = Column(String)  # Normal, Field, Continuous, Quick-Play, Ritual, Equip

    __mapper_args__ = {'polymorphic_identity': 'SPELL'}

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'attribute': 'SPELL',
            'type':      self.subtype,
        })
        return d


class TrapCard(Card):
    __tablename__ = 'trap_cards'

    cid     = Column(String, ForeignKey('cards.cid'), primary_key=True)
    subtype = Column(String)  # Normal, Continuous, Counter

    __mapper_args__ = {'polymorphic_identity': 'TRAP'}

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'attribute': 'TRAP',
            'type':      self.subtype,
        })
        return d


class SavedDeck(Base):
    __tablename__ = 'saved_decks'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String, nullable=False, unique=True)
    created_at = Column(String)

    entries = relationship('DeckEntry', back_populates='deck', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'created_at': self.created_at,
            'card_count': len(self.entries),
        }


class DeckEntry(Base):
    __tablename__ = 'deck_entries'

    id       = Column(Integer, primary_key=True, autoincrement=True)
    deck_id  = Column(Integer, ForeignKey('saved_decks.id'), nullable=False)
    card_cid = Column(String, ForeignKey('cards.cid'))
    quantity = Column(Integer, default=1)

    card = relationship('Card')
    deck = relationship('SavedDeck', back_populates='entries')


class Setting(Base):
    __tablename__ = 'settings'

    key   = Column(String, primary_key=True)
    value = Column(String, nullable=True)


# ── Manager ───────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self, db_path='yugioh.db'):
        db_url = f'sqlite:///{db_path}'
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def init_db(self, search_dir='.'):
        """Scans search_dir for scraper JSON files and upserts any new cards."""
        json_files = glob.glob(os.path.join(search_dir, '*.json'))
        added = 0
        with self.Session() as session:
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        cards_data = json.load(f)
                    if not isinstance(cards_data, list):
                        continue
                    for data in cards_data:
                        if not isinstance(data, dict) or not data.get('cid'):
                            continue

                        cid       = data['cid']
                        attr      = data.get('attribute', '')
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
                        added += 1

                except (json.JSONDecodeError, OSError):
                    continue
            session.commit()

        if added:
            print(f'[DB] Synced {added} card entries from {len(json_files)} JSON file(s).')

    def get_cards(self):
        with self.Session() as session:
            cards = session.query(Card).order_by(Card.name).all()
            return [c.to_dict() for c in cards]

    # ── Decks ──────────────────────────────────────────────────────────────────

    def create_deck(self, name):
        from datetime import datetime
        with self.Session() as session:
            deck = SavedDeck(name=name, created_at=datetime.now().isoformat())
            session.add(deck)
            session.commit()
            return deck.id

    def get_all_decks(self):
        with self.Session() as session:
            decks = session.query(SavedDeck).order_by(SavedDeck.name).all()
            return [d.to_dict() for d in decks]

    def delete_deck(self, deck_id):
        with self.Session() as session:
            deck = session.query(SavedDeck).filter(SavedDeck.id == deck_id).first()
            if deck:
                session.delete(deck)
                session.commit()
                return True
            return False

    def add_card_to_deck(self, deck_id, card_cid):
        with self.Session() as session:
            entry = session.query(DeckEntry).filter(
                DeckEntry.deck_id == deck_id,
                DeckEntry.card_cid == card_cid
            ).first()

            if entry:
                if entry.quantity < 3:
                    entry.quantity += 1
                    session.commit()
                    return True
                return False

            total = sum(
                e.quantity for e in
                session.query(DeckEntry).filter(DeckEntry.deck_id == deck_id).all()
            )
            if total >= 60:
                return False

            session.add(DeckEntry(deck_id=deck_id, card_cid=card_cid, quantity=1))
            session.commit()
            return True

    def remove_card_from_deck(self, deck_id, card_cid):
        with self.Session() as session:
            entry = session.query(DeckEntry).filter(
                DeckEntry.deck_id == deck_id,
                DeckEntry.card_cid == card_cid
            ).first()
            if entry:
                if entry.quantity > 1:
                    entry.quantity -= 1
                else:
                    session.delete(entry)
                session.commit()
                return True
            return False

    def get_deck_cards(self, deck_id):
        with self.Session() as session:
            entries = session.query(DeckEntry).filter(DeckEntry.deck_id == deck_id).all()
            result = []
            for entry in entries:
                if entry.card:
                    d = entry.card.to_dict()
                    d['quantity']  = entry.quantity
                    d['entry_id']  = entry.id
                    result.append(d)
            return result

    def get_deck_card_count(self, deck_id):
        with self.Session() as session:
            entries = session.query(DeckEntry).filter(DeckEntry.deck_id == deck_id).all()
            return sum(e.quantity for e in entries)

    # ── Settings ───────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        with self.Session() as session:
            row = session.query(Setting).filter(Setting.key == key).first()
            if row is None:
                return default
            return row.value  # always a string or None

    def set_setting(self, key: str, value):
        with self.Session() as session:
            row = session.query(Setting).filter(Setting.key == key).first()
            if row is None:
                session.add(Setting(key=key, value=value))
            else:
                row.value = value
            session.commit()
