import os
import json
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

class Card(Base):
    __tablename__ = 'cards'

    cid = Column(String, primary_key=True)
    type = Column(String)
    name = Column(String)
    image_name = Column(String)
    attribute = Column(String)
    level = Column(String)
    atk = Column(String)
    def_ = Column('def', String) # 'def' is a Python keyword, map it to 'def_'
    text = Column(String)
    image_url = Column(String)

    def to_dict(self):
        return {
            'cid': self.cid,
            'type': self.type,
            'name': self.name,
            'image_name': self.image_name,
            'attribute': self.attribute,
            'level': self.level,
            'atk': self.atk,
            'def': self.def_,
            'text': self.text,
            'image_url': self.image_url
        }

class SavedDeck(Base):
    __tablename__ = 'saved_decks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(String)

    entries = relationship("DeckEntry", back_populates="deck", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at,
            'card_count': len(self.entries)
        }

class DeckEntry(Base):
    __tablename__ = 'deck_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_id = Column(Integer, ForeignKey('saved_decks.id'), nullable=False)
    card_cid = Column(String, ForeignKey('cards.cid'))
    quantity = Column(Integer, default=1)

    card = relationship("Card")
    deck = relationship("SavedDeck", back_populates="entries")

class DatabaseManager:
    def __init__(self, db_path="yugioh.db"):
        db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        
        # Ensure tables are created
        Base.metadata.create_all(self.engine)

    def init_db(self, json_file="normal_monsters.json"):
        """Populates the database from a JSON file if it's empty."""
        with self.Session() as session:
            count = session.query(Card).count()
            if count == 0:
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        cards_data = json.load(f)
                        
                        card_objects = []
                        for data in cards_data:
                            card = Card(
                                cid=data.get('cid', ''),
                                type=data.get('type', ''),
                                name=data.get('name', ''),
                                image_name=data.get('image_name', ''),
                                attribute=data.get('attribute', ''),
                                level=data.get('level', ''),
                                atk=str(data.get('atk', '')),
                                def_=str(data.get('def', '')),
                                text=data.get('text', ''),
                                image_url=data.get('image_url', '')
                            )
                            card_objects.append(card)
                            
                        session.add_all(card_objects)
                        session.commit()

    def get_cards(self):
        """Returns a list of dictionaries representing all cards in the database."""
        with self.Session() as session:
            cards = session.query(Card).order_by(Card.name).all()
            return [card.to_dict() for card in cards]

    def create_deck(self, name):
        """Creates a new deck with the given name."""
        from datetime import datetime
        with self.Session() as session:
            deck = SavedDeck(name=name, created_at=datetime.now().isoformat())
            session.add(deck)
            session.commit()
            return deck.id

    def get_all_decks(self):
        """Returns a list of all saved decks."""
        with self.Session() as session:
            decks = session.query(SavedDeck).order_by(SavedDeck.name).all()
            return [deck.to_dict() for deck in decks]

    def delete_deck(self, deck_id):
        """Deletes a deck and all its entries."""
        with self.Session() as session:
            deck = session.query(SavedDeck).filter(SavedDeck.id == deck_id).first()
            if deck:
                session.delete(deck)
                session.commit()
                return True
            return False

    def add_card_to_deck(self, deck_id, card_cid):
        """Adds a card to a specific deck. Returns True if successful."""
        with self.Session() as session:
            # Check if card already exists in deck
            entry = session.query(DeckEntry).filter(
                DeckEntry.deck_id == deck_id,
                DeckEntry.card_cid == card_cid
            ).first()

            if entry:
                # Yu-Gi-Oh allows max 3 copies of a card
                if entry.quantity < 3:
                    entry.quantity += 1
                    session.commit()
                    return True
                return False
            else:
                # Check total card count (main deck limit is 40-60 cards)
                total_cards = session.query(DeckEntry).filter(
                    DeckEntry.deck_id == deck_id
                ).all()
                total_count = sum(e.quantity for e in total_cards)

                if total_count >= 60:
                    return False

                entry = DeckEntry(deck_id=deck_id, card_cid=card_cid, quantity=1)
                session.add(entry)
                session.commit()
                return True

    def remove_card_from_deck(self, deck_id, card_cid):
        """Removes one copy of a card from a deck."""
        with self.Session() as session:
            entry = session.query(DeckEntry).filter(
                DeckEntry.deck_id == deck_id,
                DeckEntry.card_cid == card_cid
            ).first()

            if entry:
                if entry.quantity > 1:
                    entry.quantity -= 1
                    session.commit()
                else:
                    session.delete(entry)
                    session.commit()
                return True
            return False

    def get_deck_cards(self, deck_id):
        """Returns all cards in a specific deck with their quantities."""
        with self.Session() as session:
            entries = session.query(DeckEntry).filter(DeckEntry.deck_id == deck_id).all()
            result = []
            for entry in entries:
                if entry.card:
                    card_dict = entry.card.to_dict()
                    card_dict['quantity'] = entry.quantity
                    card_dict['entry_id'] = entry.id
                    result.append(card_dict)
            return result

    def get_deck_card_count(self, deck_id):
        """Returns the total number of cards in a deck."""
        with self.Session() as session:
            entries = session.query(DeckEntry).filter(DeckEntry.deck_id == deck_id).all()
            return sum(e.quantity for e in entries)
