import arcade
import arcade.gui
import constants
from database import DatabaseManager


class DeckManagementView(arcade.View):
    """View for managing saved decks (view, delete, rename)."""

    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        self.db = DatabaseManager()
        self.ui_manager = arcade.gui.UIManager()

        self.decks = []
        self.selected_deck_id = None

    def setup(self):
        """Initialize the deck management view."""
        self.ui_manager.enable()
        self.load_decks()
        self.create_ui()

    def load_decks(self):
        """Load all decks from database."""
        self.decks = self.db.get_all_decks()

    def create_ui(self):
        """Create UI elements."""
        self.ui_manager.clear()

        # Back button at top
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=10)

        back_button = arcade.gui.UIFlatButton(text="Back to Menu", width=200)
        back_button.on_click = self.on_back_click

        delete_button = arcade.gui.UIFlatButton(text="Delete Selected Deck", width=200)
        delete_button.on_click = self.on_delete_click

        v_box.add(back_button)
        v_box.add(delete_button)

        anchor = self.ui_manager.add(arcade.gui.UIAnchorLayout())
        anchor.add(child=v_box, anchor_x="right", anchor_y="top",
                   align_x=-20, align_y=-20)

    def on_draw(self):
        """Render the deck management view."""
        self.clear()

        # Title
        arcade.draw_text(
            "Manage Your Decks",
            constants.SCREEN_WIDTH / 2,
            constants.SCREEN_HEIGHT - 50,
            arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            bold=True
        )

        # Draw decks list
        if not self.decks:
            arcade.draw_text(
                "No decks found. Create one in the Deck Builder!",
                constants.SCREEN_WIDTH / 2,
                constants.SCREEN_HEIGHT / 2,
                arcade.color.LIGHT_GRAY,
                font_size=16,
                anchor_x="center"
            )
        else:
            start_y = constants.SCREEN_HEIGHT - 120
            line_height = 60

            for idx, deck in enumerate(self.decks):
                y = start_y - (idx * line_height)

                # Highlight selected deck
                is_selected = self.selected_deck_id == deck['id']
                bg_color = (80, 100, 120) if is_selected else (40, 50, 60)

                # Draw deck box
                arcade.draw_lrbt_rectangle_filled(
                    constants.SCREEN_WIDTH / 2 - 300,
                    constants.SCREEN_WIDTH / 2 + 300,
                    y - 25,
                    y + 25,
                    bg_color
                )
                arcade.draw_lrbt_rectangle_outline(
                    constants.SCREEN_WIDTH / 2 - 300,
                    constants.SCREEN_WIDTH / 2 + 300,
                    y - 25,
                    y + 25,
                    arcade.color.WHITE if is_selected else arcade.color.GRAY, 2
                )

                # Draw deck info
                deck_text = f"{deck['name']} - {deck['card_count']} cards"
                arcade.draw_text(
                    deck_text,
                    constants.SCREEN_WIDTH / 2 - 280,
                    y - 10,
                    arcade.color.WHITE,
                    font_size=14,
                    bold=is_selected
                )

                # Draw created date
                if deck.get('created_at'):
                    date_text = f"Created: {deck['created_at'][:10]}"
                    arcade.draw_text(
                        date_text,
                        constants.SCREEN_WIDTH / 2 + 150,
                        y - 10,
                        arcade.color.LIGHT_GRAY,
                        font_size=10
                    )

        # Instructions
        arcade.draw_text(
            "Click on a deck to select it | ESC: Back to menu",
            20, 20,
            arcade.color.LIGHT_GRAY,
            font_size=10
        )

        self.ui_manager.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse clicks on decks."""
        if button == arcade.MOUSE_BUTTON_LEFT:
            start_y = constants.SCREEN_HEIGHT - 120
            line_height = 60

            for idx, deck in enumerate(self.decks):
                deck_y = start_y - (idx * line_height)
                # Check if click is within deck bounds
                if (constants.SCREEN_WIDTH / 2 - 300 < x < constants.SCREEN_WIDTH / 2 + 300
                        and deck_y - 25 < y < deck_y + 25):
                    self.selected_deck_id = deck['id']
                    print(f"Selected deck: {deck['name']}")
                    break

    def on_delete_click(self, event):
        """Delete the selected deck."""
        if self.selected_deck_id:
            # Find deck name for confirmation
            deck_name = next(
                (d['name'] for d in self.decks if d['id'] == self.selected_deck_id),
                "Unknown"
            )

            success = self.db.delete_deck(self.selected_deck_id)
            if success:
                print(f"Deleted deck: {deck_name}")
                self.selected_deck_id = None
                self.load_decks()
            else:
                print("Failed to delete deck")
        else:
            print("No deck selected")

    def on_back_click(self, event):
        """Return to main menu."""
        from menu_view import MenuView
        menu = MenuView()
        self.window.show_view(menu)

    def on_key_press(self, symbol, modifiers):
        """Handle key presses."""
        if symbol == arcade.key.ESCAPE:
            self.on_back_click(None)

    def on_hide_view(self):
        """Clean up when leaving view."""
        self.ui_manager.disable()
