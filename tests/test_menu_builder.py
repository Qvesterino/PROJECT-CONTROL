"""Tests for Menu Builder Pattern."""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import Mock, patch

from project_control.ui.menu_builder import (
    MenuBuilder, MenuItem, MenuSeparator, create_menu
)


class TestMenuItem(TestCase):
    """Test MenuItem class."""

    def test_create_item(self) -> None:
        """Test creating a menu item."""
        item = MenuItem(key="1", label="Test Item")
        self.assertEqual(item.key, "1")
        self.assertEqual(item.label, "Test Item")
        self.assertIsNone(item.action)
        self.assertIsNone(item.submenu)

    def test_item_with_action(self) -> None:
        """Test creating an item with an action."""
        action = Mock()
        item = MenuItem(key="a", label="Action Item", action=action)
        self.assertIsNotNone(item.action)
        self.assertEqual(item.action, action)

    def test_item_with_submenu(self) -> None:
        """Test creating an item with a submenu."""
        submenu = MenuBuilder("Submenu")
        item = MenuItem(key="s", label="Submenu Item", submenu=submenu)
        self.assertIsNotNone(item.submenu)
        self.assertEqual(item.submenu, submenu)


class TestMenuSeparator(TestCase):
    """Test MenuSeparator class."""

    def test_default_separator(self) -> None:
        """Test default separator."""
        sep = MenuSeparator()
        result = sep.render()
        self.assertEqual(result, "─" * 40)

    def test_custom_separator(self) -> None:
        """Test custom separator."""
        sep = MenuSeparator(char="=", length=20)
        result = sep.render()
        self.assertEqual(result, "=" * 20)


class TestMenuBuilder(TestCase):
    """Test MenuBuilder class."""

    def test_empty_menu(self) -> None:
        """Test creating an empty menu."""
        menu = MenuBuilder("Test Menu")
        result = menu.render()
        self.assertIn("Test Menu", result)
        self.assertIn("=" * 9, result)  # len("Test Menu")

    def test_add_single_item(self) -> None:
        """Test adding a single item."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First Item")
        result = menu.render()
        self.assertIn("1)", result)
        self.assertIn("First Item", result)

    def test_add_multiple_items(self) -> None:
        """Test adding multiple items."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")
        menu.add_item(key="2", label="Second")
        menu.add_item(key="3", label="Third")

        result = menu.render()
        self.assertIn("1)", result)
        self.assertIn("2)", result)
        self.assertIn("3)", result)
        self.assertIn("First", result)
        self.assertIn("Second", result)
        self.assertIn("Third", result)

    def test_auto_assign_keys(self) -> None:
        """Test auto-assignment of numeric keys."""
        menu = MenuBuilder()
        menu.add_item(label="First")
        menu.add_item(label="Second")
        menu.add_item(label="Third")

        self.assertEqual(menu.items[0].key, "1")
        self.assertEqual(menu.items[1].key, "2")
        self.assertEqual(menu.items[2].key, "3")

    def test_add_separator(self) -> None:
        """Test adding a separator."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")
        menu.add_separator()
        menu.add_item(key="2", label="Second")

        result = menu.render()
        lines = result.split("\n")
        # Should have an empty line between items
        self.assertTrue(any(line.strip() == "" for line in lines))

    def test_add_header(self) -> None:
        """Test adding a section header."""
        menu = MenuBuilder()
        menu.add_header("Section 1")
        menu.add_item(key="1", label="Item 1")

        result = menu.render()
        self.assertIn("Section 1", result)

    def test_chain_methods(self) -> None:
        """Test method chaining."""
        menu = (MenuBuilder()
                .add_item(key="1", label="First")
                .add_item(key="2", label="Second")
                .add_separator()
                .add_item(key="3", label="Third"))

        self.assertEqual(len(menu.items), 3)
        self.assertIn("1)", menu.render())
        self.assertIn("2)", menu.render())
        self.assertIn("3)", menu.render())

    def test_add_submenu(self) -> None:
        """Test adding a submenu."""
        submenu = MenuBuilder("Submenu")
        submenu.add_item(key="a", label="Sub Item")

        menu = MenuBuilder()
        menu.add_submenu(key="s", label="Go to Submenu", submenu=submenu)

        self.assertEqual(len(menu.items), 1)
        self.assertIsNotNone(menu.items[0].submenu)

    def test_get_item_by_key(self) -> None:
        """Test finding an item by key."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")
        menu.add_item(key="2", label="Second")

        item = menu.get_item_by_key("1")
        self.assertIsNotNone(item)
        self.assertEqual(item.label, "First")

        item = menu.get_item_by_key("2")
        self.assertIsNotNone(item)
        self.assertEqual(item.label, "Second")

        item = menu.get_item_by_key("3")
        self.assertIsNone(item)

    def test_case_insensitive_key(self) -> None:
        """Test that key lookup is case-insensitive."""
        menu = MenuBuilder()
        menu.add_item(key="Q", label="Quit")

        item = menu.get_item_by_key("q")
        self.assertIsNotNone(item)
        self.assertEqual(item.label, "Quit")

    def test_execute_action(self) -> None:
        """Test executing an item's action."""
        action = Mock(return_value="result")
        menu = MenuBuilder()
        menu.add_item(key="1", label="Action Item", action=action)

        result = menu.execute("1")
        self.assertEqual(result, "result")
        action.assert_called_once()

    def test_execute_nonexistent_key(self) -> None:
        """Test executing a non-existent key."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="Item")

        result = menu.execute("999")
        self.assertIsNone(result)

    def test_get_submenu(self) -> None:
        """Test getting a submenu."""
        submenu = MenuBuilder("Submenu")
        menu = MenuBuilder()
        menu.add_submenu(key="s", label="Submenu", submenu=submenu)

        result = menu.get_submenu("s")
        self.assertIsNotNone(result)
        self.assertEqual(result, submenu)

    def test_has_submenu(self) -> None:
        """Test checking if an item has a submenu."""
        submenu = MenuBuilder("Submenu")
        menu = MenuBuilder()
        menu.add_item(key="1", label="Regular Item")
        menu.add_submenu(key="s", label="Submenu", submenu=submenu)

        self.assertFalse(menu.has_submenu("1"))
        self.assertTrue(menu.has_submenu("s"))

    def test_is_valid_key(self) -> None:
        """Test validating keys."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")
        menu.add_item(key="a", label="Alpha")

        self.assertTrue(menu.is_valid_key("1"))
        self.assertTrue(menu.is_valid_key("a"))
        self.assertTrue(menu.is_valid_key("A"))  # Case-insensitive
        self.assertFalse(menu.is_valid_key("2"))
        self.assertFalse(menu.is_valid_key("b"))

    def test_get_all_keys(self) -> None:
        """Test getting all keys."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")
        menu.add_item(key="2", label="Second")
        menu.add_item(key="a", label="Alpha")

        keys = menu.get_all_keys()
        self.assertEqual(sorted(keys), ["1", "2", "a"])

    def test_render_with_descriptions(self) -> None:
        """Test rendering with descriptions."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="Item 1", description="Description 1")
        menu.add_item(key="2", label="Item 2", description="Description 2")

        result = menu.render(show_descriptions=True)
        self.assertIn("— Description 1", result)
        self.assertIn("— Description 2", result)

    def test_render_without_keys(self) -> None:
        """Test rendering without showing keys."""
        menu = MenuBuilder()
        menu.add_item(key="1", label="First")

        result = menu.render(show_keys=False)
        self.assertNotIn("1)", result)
        self.assertIn("First", result)

    def test_add_prebuilt_item(self) -> None:
        """Test adding a pre-built MenuItem."""
        item = MenuItem(key="x", label="Custom Item")
        menu = MenuBuilder()
        menu.add_item(item=item)

        self.assertEqual(len(menu.items), 1)
        self.assertEqual(menu.items[0].key, "x")

    def test_print_menu(self) -> None:
        """Test printing menu (should not crash)."""
        menu = MenuBuilder("Test")
        menu.add_item(key="1", label="Item")

        # Should not raise exception
        menu.print()


class TestCreateMenu(TestCase):
    """Test create_menu convenience function."""

    def test_create_menu(self) -> None:
        """Test creating a menu with the convenience function."""
        menu = create_menu("My Menu")
        self.assertIsInstance(menu, MenuBuilder)
        self.assertEqual(menu.title, "My Menu")

    def test_create_menu_no_title(self) -> None:
        """Test creating a menu without a title."""
        menu = create_menu()
        self.assertIsInstance(menu, MenuBuilder)
        self.assertIsNone(menu.title)
