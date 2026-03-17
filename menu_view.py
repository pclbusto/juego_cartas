import arcade
import arcade.gui
import constants


class MenuView(arcade.View):
    """Main menu for the card game."""

    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.DARK_MIDNIGHT_BLUE)

        self.ui_manager = arcade.gui.UIManager()

    def on_show_view(self):
        """Called when switching to this view."""
        self.setup()

    def setup(self):
        """Set up the menu UI."""
        self.ui_manager.enable()
        self.ui_manager.clear()

        # Create a vertical box for buttons
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)

        # Title
        title_label = arcade.gui.UILabel(
            text="YU-GI-OH Style Card Game",
            font_size=24,
            text_color=arcade.color.WHITE,
            bold=True
        )

        # Deck Builder button
        deck_builder_button = arcade.gui.UIFlatButton(
            text="Deck Builder",
            width=250,
            height=50
        )
        deck_builder_button.on_click = self.on_deck_builder_click

        # Play Game button
        play_button = arcade.gui.UIFlatButton(
            text="Play Game",
            width=250,
            height=50
        )
        play_button.on_click = self.on_play_click

        # Manage Decks button
        manage_decks_button = arcade.gui.UIFlatButton(
            text="Manage Decks",
            width=250,
            height=50
        )
        manage_decks_button.on_click = self.on_manage_decks_click

        # Quit button
        quit_button = arcade.gui.UIFlatButton(
            text="Quit",
            width=250,
            height=50
        )
        quit_button.on_click = self.on_quit_click

        # Add widgets to layout
        v_box.add(title_label)
        v_box.add(deck_builder_button)
        v_box.add(play_button)
        v_box.add(manage_decks_button)
        v_box.add(quit_button)

        # Center the layout
        anchor = self.ui_manager.add(arcade.gui.UIAnchorLayout())
        anchor.add(
            child=v_box,
            anchor_x="center",
            anchor_y="center"
        )

    def on_draw(self):
        """Render the menu."""
        self.clear()

        # Draw title at top
        arcade.draw_text(
            "Welcome to the Card Game",
            constants.SCREEN_WIDTH / 2,
            constants.SCREEN_HEIGHT - 100,
            arcade.color.GOLD,
            font_size=30,
            anchor_x="center",
            bold=True
        )

        # Draw version info
        arcade.draw_text(
            "v1.0 - Deck Builder Edition",
            constants.SCREEN_WIDTH / 2,
            50,
            arcade.color.LIGHT_GRAY,
            font_size=12,
            anchor_x="center"
        )

        self.ui_manager.draw()

    def on_deck_builder_click(self, event):
        """Open the deck builder."""
        from deck_builder_view import DeckBuilderView
        deck_builder = DeckBuilderView()
        deck_builder.setup()
        self.window.show_view(deck_builder)

    def on_play_click(self, event):
        """Start the game."""
        from game_view import GameView
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)

    def on_manage_decks_click(self, event):
        """Open deck management view."""
        from deck_management_view import DeckManagementView
        deck_mgmt = DeckManagementView()
        deck_mgmt.setup()
        self.window.show_view(deck_mgmt)

    def on_quit_click(self, event):
        """Quit the game."""
        arcade.exit()

    def on_hide_view(self):
        """Clean up when leaving view."""
        self.ui_manager.disable()

    def on_key_press(self, symbol, modifiers):
        """Handle key presses."""
        if symbol == arcade.key.ESCAPE:
            arcade.exit()
