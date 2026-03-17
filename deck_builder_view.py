import arcade
import arcade.gui
import constants
from database import DatabaseManager
import os

class CardDisplay(arcade.Sprite):
    """Visual representation of a card in the deck builder."""

    def __init__(self, card_data, x, y):
        # Try to load card image
        image_path = f"images/{card_data.get('image_name', '')}"

        if os.path.exists(image_path):
            super().__init__(image_path)
            # Scale to fit card dimensions
            scale_x = constants.CARD_WIDTH / self.width
            scale_y = constants.CARD_HEIGHT / self.height
            self.scale = min(scale_x, scale_y)
        else:
            # Fallback to colored rectangle if image not found
            super().__init__()
            # Create a simple solid color texture as placeholder
            from arcade import Texture
            import PIL.Image

            img = PIL.Image.new('RGBA', (int(constants.CARD_WIDTH), int(constants.CARD_HEIGHT)), (173, 216, 230, 255))
            self.texture = Texture(f"placeholder_{id(card_data)}", img)

        self.card_data = card_data
        self.center_x = x
        self.center_y = y
        self.selected = False

    def draw_info(self):
        """Draw card information overlay."""
        if self.selected:
            half_w = (constants.CARD_WIDTH + 4) / 2
            half_h = (constants.CARD_HEIGHT + 4) / 2
            arcade.draw_lrbt_rectangle_outline(
                self.center_x - half_w, self.center_x + half_w,
                self.center_y - half_h, self.center_y + half_h,
                arcade.color.YELLOW, 3
            )

        # Draw card name below
        arcade.draw_text(
            self.card_data.get('name', 'Unknown')[:15],
            self.center_x, self.center_y - constants.CARD_HEIGHT / 2 - 20,
            arcade.color.WHITE,
            font_size=9,
            anchor_x="center",
            width=constants.CARD_WIDTH,
            align="center"
        )


class DeckBuilderView(arcade.View):
    """View for building and editing decks."""

    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        self.db = DatabaseManager()
        self.db.init_db()

        # UI Manager
        self.ui_manager = arcade.gui.UIManager()

        # Card collection data
        self.all_cards = []
        self.available_cards_sprites = arcade.SpriteList()
        self.current_deck_sprites = arcade.SpriteList()

        # Current deck info
        self.current_deck_id = None
        self.current_deck_name = "New Deck"
        self.deck_cards = {}  # card_cid -> quantity

        # Scroll and pagination
        self.scroll_offset = 0
        self.cards_per_row = 8
        self.rows_visible = 2

        # Selected card for detail view
        self.selected_card = None

        # Filter text
        self.filter_text = ""

    def setup(self):
        """Initialize the deck builder."""
        self.ui_manager.enable()

        # Load all available cards
        self.all_cards = self.db.get_cards()

        # Check if there are any saved decks
        decks = self.db.get_all_decks()
        if decks:
            # Load first deck
            self.current_deck_id = decks[0]['id']
            self.current_deck_name = decks[0]['name']
            self.load_current_deck()
        else:
            # Create a default deck
            self.current_deck_id = self.db.create_deck("My First Deck")
            self.current_deck_name = "My First Deck"

        self.update_available_cards_display()
        self.update_deck_display()

        # Create UI elements
        self.create_ui()

    def create_ui(self):
        """Create UI buttons and labels."""
        # Clear existing UI
        self.ui_manager.clear()

        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=10)

        # Back button
        back_button = arcade.gui.UIFlatButton(text="Back to Game", width=150)
        back_button.on_click = self.on_back_button_click

        # New Deck button
        new_deck_button = arcade.gui.UIFlatButton(text="New Deck", width=150)
        new_deck_button.on_click = self.on_new_deck_click

        # Save button
        save_button = arcade.gui.UIFlatButton(text="Save Deck", width=150)
        save_button.on_click = self.on_save_deck_click

        v_box.add(back_button)
        v_box.add(new_deck_button)
        v_box.add(save_button)

        # Anchor to top-right
        anchor = self.ui_manager.add(arcade.gui.UIAnchorLayout())
        anchor.add(child=v_box, anchor_x="right", anchor_y="top",
                   align_x=-20, align_y=-20)

    def load_current_deck(self):
        """Load cards from current deck into memory."""
        if self.current_deck_id:
            deck_cards = self.db.get_deck_cards(self.current_deck_id)
            self.deck_cards = {card['cid']: card['quantity'] for card in deck_cards}
        else:
            self.deck_cards = {}

    def update_available_cards_display(self):
        """Update the display of available cards to add to deck."""
        self.available_cards_sprites.clear()

        # Filter cards based on search
        filtered_cards = [
            card for card in self.all_cards
            if self.filter_text.lower() in card['name'].lower()
        ]

        # Calculate visible range
        start_idx = self.scroll_offset * self.cards_per_row
        end_idx = start_idx + (self.cards_per_row * self.rows_visible)
        visible_cards = filtered_cards[start_idx:end_idx]

        # Position cards in grid
        start_x = 150
        start_y = constants.SCREEN_HEIGHT - 150

        for idx, card_data in enumerate(visible_cards):
            row = idx // self.cards_per_row
            col = idx % self.cards_per_row

            x = start_x + col * (constants.CARD_WIDTH + 10)
            y = start_y - row * (constants.CARD_HEIGHT + 40)

            card_sprite = CardDisplay(card_data, x, y)
            self.available_cards_sprites.append(card_sprite)

    def update_deck_display(self):
        """Update the display of cards currently in the deck."""
        self.current_deck_sprites.clear()

        # Get cards in deck
        deck_cards = self.db.get_deck_cards(self.current_deck_id) if self.current_deck_id else []

        # Position cards in a row at bottom
        start_x = 150
        start_y = 100

        for idx, card_data in enumerate(deck_cards[:10]):  # Show first 10
            x = start_x + idx * (constants.CARD_WIDTH + 10)
            card_sprite = CardDisplay(card_data, x, start_y)
            self.current_deck_sprites.append(card_sprite)

    def on_draw(self):
        """Render the deck builder."""
        self.clear()

        # Draw sections
        # Available cards section
        arcade.draw_lrbt_rectangle_filled(
            20,
            constants.SCREEN_WIDTH - 20,
            constants.SCREEN_HEIGHT - 450,
            constants.SCREEN_HEIGHT - 50,
            (40, 40, 60)
        )
        arcade.draw_text(
            "Available Cards (Click to add)",
            150, constants.SCREEN_HEIGHT - 50,
            arcade.color.WHITE, font_size=16, bold=True
        )

        # Current deck section
        arcade.draw_lrbt_rectangle_filled(
            20,
            constants.SCREEN_WIDTH - 20,
            30,
            210,
            (30, 50, 40)
        )

        # Deck info
        deck_count = self.db.get_deck_card_count(self.current_deck_id) if self.current_deck_id else 0
        arcade.draw_text(
            f"Current Deck: {self.current_deck_name} ({deck_count} cards)",
            150, 210,
            arcade.color.WHITE, font_size=14, bold=True
        )

        # Draw cards
        self.available_cards_sprites.draw()
        for sprite in self.available_cards_sprites:
            sprite.draw_info()

        self.current_deck_sprites.draw()
        for sprite in self.current_deck_sprites:
            sprite.draw_info()

        # Draw selected card detail
        if self.selected_card:
            self.draw_card_detail()

        # Draw UI
        self.ui_manager.draw()

        # Instructions
        arcade.draw_text(
            "Left Click: Add to deck | Right Click: Remove | Mouse Wheel: Scroll",
            20, 20,
            arcade.color.LIGHT_GRAY, font_size=10
        )

    def draw_card_detail(self):
        """Draw detailed information about selected card."""
        detail_x = constants.SCREEN_WIDTH - 250
        detail_y = constants.SCREEN_HEIGHT / 2

        # Background
        arcade.draw_lrbt_rectangle_filled(
            detail_x - 110, detail_x + 110,
            detail_y - 200, detail_y + 200,
            (20, 20, 30)
        )
        arcade.draw_lrbt_rectangle_outline(
            detail_x - 110, detail_x + 110,
            detail_y - 200, detail_y + 200,
            arcade.color.WHITE, 2
        )

        # Card info
        y_offset = detail_y + 180
        line_height = 20

        info_lines = [
            f"Name: {self.selected_card.get('name', 'N/A')}",
            f"Type: {self.selected_card.get('type', 'N/A')}",
            f"Attribute: {self.selected_card.get('attribute', 'N/A')}",
            f"Level: {self.selected_card.get('level', 'N/A')}",
            f"ATK: {self.selected_card.get('atk', 'N/A')}",
            f"DEF: {self.selected_card.get('def', 'N/A')}",
        ]

        for line in info_lines:
            arcade.draw_text(
                line, detail_x - 100, y_offset,
                arcade.color.WHITE, font_size=10,
                width=190
            )
            y_offset -= line_height

        # Card text
        y_offset -= 10
        card_text = self.selected_card.get('text', 'No description')
        arcade.draw_text(
            card_text, detail_x - 100, y_offset,
            arcade.color.LIGHT_GRAY, font_size=9,
            width=190, multiline=True
        )

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse clicks."""
        # Check if clicked on available cards
        cards = arcade.get_sprites_at_point((x, y), self.available_cards_sprites)
        if cards:
            clicked_card = cards[0]

            if button == arcade.MOUSE_BUTTON_LEFT:
                # Add to deck
                if self.current_deck_id:
                    success = self.db.add_card_to_deck(
                        self.current_deck_id,
                        clicked_card.card_data['cid']
                    )
                    if success:
                        self.load_current_deck()
                        self.update_deck_display()
                        print(f"Added {clicked_card.card_data['name']} to deck")
                    else:
                        print("Cannot add card (deck full or limit reached)")

            elif button == arcade.MOUSE_BUTTON_RIGHT:
                # Show detail
                self.selected_card = clicked_card.card_data

        # Check if clicked on deck cards
        deck_cards = arcade.get_sprites_at_point((x, y), self.current_deck_sprites)
        if deck_cards and button == arcade.MOUSE_BUTTON_LEFT:
            clicked_card = deck_cards[0]
            # Remove from deck
            if self.current_deck_id:
                self.db.remove_card_from_deck(
                    self.current_deck_id,
                    clicked_card.card_data['cid']
                )
                self.load_current_deck()
                self.update_deck_display()
                print(f"Removed {clicked_card.card_data['name']} from deck")

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """Handle mouse wheel scrolling."""
        if scroll_y > 0:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        else:
            max_offset = len(self.all_cards) // self.cards_per_row
            self.scroll_offset = min(max_offset, self.scroll_offset + 1)

        self.update_available_cards_display()

    def on_key_press(self, symbol, modifiers):
        """Handle key presses."""
        if symbol == arcade.key.ESCAPE:
            self.on_back_button_click(None)

    def on_back_button_click(self, event):
        """Return to the game view."""
        from game_view import GameView
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)

    def on_new_deck_click(self, event):
        """Create a new deck."""
        # Simple naming scheme for now
        deck_count = len(self.db.get_all_decks())
        new_name = f"Deck {deck_count + 1}"
        self.current_deck_id = self.db.create_deck(new_name)
        self.current_deck_name = new_name
        self.load_current_deck()
        self.update_deck_display()
        print(f"Created new deck: {new_name}")

    def on_save_deck_click(self, event):
        """Save the current deck (already auto-saved)."""
        if self.current_deck_id:
            count = self.db.get_deck_card_count(self.current_deck_id)
            print(f"Deck '{self.current_deck_name}' saved with {count} cards")

    def on_hide_view(self):
        """Clean up when leaving view."""
        self.ui_manager.disable()
