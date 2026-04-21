"""Menu Builder Pattern for dynamic menu construction."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


class MenuItem:
    """A single menu item."""

    def __init__(
        self,
        key: str,
        label: str,
        action: Optional[Callable[[], Any]] = None,
        submenu: Optional["MenuBuilder"] = None,
        description: Optional[str] = None
    ):
        """Initialize a menu item.

        Args:
            key: Key to trigger this item (e.g., "1", "a", "q")
            label: Display label for the item
            action: Function to call when this item is selected
            submenu: Submenu to navigate to (if any)
            description: Optional description/hint
        """
        self.key = key
        self.label = label
        self.action = action
        self.submenu = submenu
        self.description = description


class MenuSeparator:
    """A separator in the menu."""

    def __init__(self, char: str = "─", length: int = 40):
        """Initialize a separator.

        Args:
            char: Character to use for the separator line
            length: Length of the separator
        """
        self.char = char
        self.length = length

    def render(self) -> str:
        """Render the separator."""
        return self.char * self.length


class MenuBuilder:
    """Dynamic menu builder with support for items, separators, and submenus."""

    def __init__(self, title: Optional[str] = None):
        """Initialize a menu builder.

        Args:
            title: Optional title for the menu
        """
        self.title = title
        self.items: List[MenuItem] = []
        self.separators: List[int] = []  # Indices where separators should appear
        self.headers: List[int] = []  # Indices where section headers should appear
        self.header_texts: Dict[int, str] = {}  # Header text by index
        self._next_key_index = 1  # Auto-assign numeric keys starting from 1

    def add_item(
        self,
        key: Optional[str] = None,
        label: Optional[str] = None,
        action: Optional[Callable[[], Any]] = None,
        submenu: Optional["MenuBuilder"] = None,
        description: Optional[str] = None,
        item: Optional[MenuItem] = None
    ) -> "MenuBuilder":
        """Add an item to the menu.

        Args:
            key: Key to trigger this item. If None, auto-assign numeric key.
            label: Display label. Required if item is None.
            action: Function to call when selected.
            submenu: Submenu to navigate to.
            description: Optional description.
            item: Pre-built MenuItem (overrides other params).

        Returns:
            Self for method chaining.
        """
        if item:
            self.items.append(item)
        else:
            if label is None:
                raise ValueError("Either item or label must be provided")

            if key is None:
                # Auto-assign numeric key
                key = str(self._next_key_index)
                self._next_key_index += 1

            self.items.append(MenuItem(key, label, action, submenu, description))

        return self

    def add_separator(self, char: str = "─", length: int = 40) -> "MenuBuilder":
        """Add a separator after the current items.

        Args:
            char: Character for separator line
            length: Length of separator

        Returns:
            Self for method chaining.
        """
        self.separators.append(len(self.items))
        return self

    def add_header(self, text: str) -> "MenuBuilder":
        """Add a section header before the next item.

        Args:
            text: Header text

        Returns:
            Self for method chaining.
        """
        self.headers.append(len(self.items))
        self.header_texts[len(self.items)] = text
        return self

    def add_submenu(
        self,
        key: Optional[str] = None,
        label: Optional[str] = None,
        submenu: Optional["MenuBuilder"] = None,
        description: Optional[str] = None
    ) -> "MenuBuilder":
        """Add a submenu item.

        Args:
            key: Key to trigger this submenu
            label: Display label
            submenu: The MenuBuilder for the submenu
            description: Optional description

        Returns:
            Self for method chaining.
        """
        if submenu is None:
            raise ValueError("submenu must be provided")

        self.add_item(key=key, label=label, submenu=submenu, description=description)
        return self

    def render(self, show_keys: bool = True, show_descriptions: bool = False) -> str:
        """Render the menu as a string.

        Args:
            show_keys: Whether to show the trigger keys
            show_descriptions: Whether to show item descriptions

        Returns:
            Rendered menu as string
        """
        lines: List[str] = []

        # Title
        if self.title:
            lines.append(self.title)
            lines.append("=" * len(self.title))
            lines.append("")

        # Items
        for i, item in enumerate(self.items):
            # Check for header before this item
            if i in self.headers:
                lines.append("")
                lines.append(f"  {self.header_texts[i]}")
                lines.append("  " + "-" * len(self.header_texts[i]))

            # Check for separator before this item
            if i in self.separators:
                lines.append("")

            # Render item
            if show_keys:
                key_part = f"{item.key}) "
            else:
                key_part = ""

            if show_descriptions and item.description:
                line = f"  {key_part}{item.label} — {item.description}"
            else:
                line = f"  {key_part}{item.label}"

            lines.append(line)

        # Add separator at the end
        if self.items:
            lines.append("")

        return "\n".join(lines)

    def print(self, show_keys: bool = True, show_descriptions: bool = False) -> None:
        """Print the menu to stdout.

        Args:
            show_keys: Whether to show the trigger keys
            show_descriptions: Whether to show item descriptions
        """
        print(self.render(show_keys, show_descriptions))

    def get_item_by_key(self, key: str) -> Optional[MenuItem]:
        """Find a menu item by its key.

        Args:
            key: The key to search for

        Returns:
            The MenuItem if found, None otherwise
        """
        for item in self.items:
            if item.key.lower() == key.lower():
                return item
        return None

    def execute(self, key: str) -> Any:
        """Execute the action for the given key.

        Args:
            key: The key of the item to execute

        Returns:
            The result of the action, or None if no action
        """
        item = self.get_item_by_key(key)
        if item is None:
            return None

        if item.action is not None:
            return item.action()

        return None

    def get_submenu(self, key: str) -> Optional["MenuBuilder"]:
        """Get the submenu for the given key.

        Args:
            key: The key of the submenu item

        Returns:
            The MenuBuilder for the submenu, or None
        """
        item = self.get_item_by_key(key)
        if item and item.submenu:
            return item.submenu
        return None

    def has_submenu(self, key: str) -> bool:
        """Check if the given key has a submenu.

        Args:
            key: The key to check

        Returns:
            True if the key has a submenu, False otherwise
        """
        return self.get_submenu(key) is not None

    def is_valid_key(self, key: str) -> bool:
        """Check if the given key is valid for this menu.

        Args:
            key: The key to validate

        Returns:
            True if the key exists, False otherwise
        """
        return self.get_item_by_key(key) is not None

    def get_all_keys(self) -> List[str]:
        """Get all valid keys for this menu.

        Returns:
            List of all keys
        """
        return [item.key for item in self.items]


def create_menu(title: Optional[str] = None) -> MenuBuilder:
    """Convenience function to create a new MenuBuilder.

    Args:
        title: Optional title for the menu

    Returns:
        New MenuBuilder instance
    """
    return MenuBuilder(title)
