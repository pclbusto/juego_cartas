"""
Script to initialize the database with cards from JSON and create a sample deck.
"""
from database import DatabaseManager

def main():
    print("Initializing database...")
    db = DatabaseManager()

    # Initialize database with cards from JSON
    db.init_db("normal_monsters.json")

    # Check how many cards were loaded
    cards = db.get_cards()
    print(f"Loaded {len(cards)} cards from database")

    # List first few cards
    if cards:
        print("\nFirst 5 cards:")
        for card in cards[:5]:
            print(f"  - {card['name']} (ATK: {card['atk']}, DEF: {card['def']})")

    # Check if any decks exist
    decks = db.get_all_decks()
    print(f"\nFound {len(decks)} existing decks")

    if not decks:
        print("\nCreating sample deck...")
        deck_id = db.create_deck("Starter Deck")
        print(f"Created deck with ID: {deck_id}")

        # Add some cards to the deck
        print("Adding cards to deck...")
        cards_to_add = cards[:10]  # Add first 10 cards
        for card in cards_to_add:
            success = db.add_card_to_deck(deck_id, card['cid'])
            if success:
                print(f"  Added: {card['name']}")
            else:
                print(f"  Failed to add: {card['name']}")

        # Show deck contents
        deck_cards = db.get_deck_cards(deck_id)
        total = db.get_deck_card_count(deck_id)
        print(f"\nDeck now has {total} cards:")
        for card in deck_cards:
            print(f"  - {card['name']} x{card['quantity']}")

    print("\nDatabase initialization complete!")

if __name__ == "__main__":
    main()
