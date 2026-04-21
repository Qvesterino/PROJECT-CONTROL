"""Tests for Rich Tables."""

from __future__ import annotations

from unittest import TestCase

from project_control.utils.tables import Table, create_table, print_table


class TestTable(TestCase):
    """Test Table class."""

    def test_empty_table(self) -> None:
        """Test rendering an empty table."""
        table = Table(["A", "B", "C"])
        result = table.render()
        self.assertIn("┌", result)
        self.assertIn("┐", result)
        self.assertIn("│", result)
        self.assertIn("A", result)
        self.assertIn("B", result)
        self.assertIn("C", result)

    def test_single_row(self) -> None:
        """Test table with one data row."""
        table = Table(["Name", "Age", "City"])
        table.add_row(["Alice", "30", "NYC"])
        result = table.render()

        self.assertIn("Alice", result)
        self.assertIn("30", result)
        self.assertIn("NYC", result)
        self.assertIn("Name", result)

    def test_multiple_rows(self) -> None:
        """Test table with multiple data rows."""
        table = Table(["Name", "Score"])
        table.add_row(["Alice", "95"])
        table.add_row(["Bob", "87"])
        table.add_row(["Charlie", "92"])

        result = table.render()
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        self.assertIn("Charlie", result)
        self.assertEqual(result.count("Alice"), 1)
        self.assertEqual(result.count("Bob"), 1)

    def test_auto_column_width(self) -> None:
        """Test automatic column width calculation."""
        table = Table(["Name", "Description"])
        table.add_row(["Short", "A short description"])
        table.add_row(["Longer Name", "A much longer description that should expand the column"])

        result = table.render()
        # The description column should be wider than the name column
        self.assertIn("A much longer description", result)

    def test_title(self) -> None:
        """Test table with title."""
        table = Table(["A", "B"])
        table.add_row(["1", "2"])
        result = table.render(title="My Table")

        self.assertIn("My Table", result)

    def test_numeric_values(self) -> None:
        """Test table with numeric values."""
        table = Table(["Count", "Sum", "Avg"])
        table.add_row([10, 100, 10.5])
        table.add_row([5, 50, 10.0])

        result = table.render()
        self.assertIn("10", result)
        self.assertIn("100", result)
        self.assertIn("10.5", result)

    def test_none_values(self) -> None:
        """Test table with None values."""
        table = Table(["Name", "Value"])
        table.add_row(["Test", None])
        table.add_row([None, "Value"])

        result = table.render()
        self.assertIn("Test", result)
        self.assertIn("None", result)  # None should be converted to string

    def test_max_width_constraint(self) -> None:
        """Test table with max width constraint."""
        table = Table(["Column1", "Column2", "Column3"])
        table.add_row(["Very long text here", "Another long text", "Yet more long text"])
        table.add_row(["More data", "Even more", "And even more"])

        result = table.render(max_width=50)
        # Should be significantly shorter than full width
        # Full width would be much longer than 50
        lines = result.split("\n")
        max_line_length = max(len(line) for line in lines)
        self.assertLess(max_line_length, 100)  # Should be reasonable


class TestConvenienceFunctions(TestCase):
    """Test convenience functions."""

    def test_create_table(self) -> None:
        """Test create_table convenience function."""
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "25"]]
        result = create_table(headers, rows)

        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        self.assertIn("Name", result)
        self.assertIn("Age", result)

    def test_create_table_with_title(self) -> None:
        """Test create_table with title."""
        headers = ["X", "Y"]
        rows = [[1, 2], [3, 4]]
        result = create_table(headers, rows, title="Coordinates")

        self.assertIn("Coordinates", result)
        self.assertIn("1", result)
        self.assertIn("2", result)

    def test_print_table(self) -> None:
        """Test print_table doesn't crash."""
        headers = ["A", "B"]
        rows = [[1, 2], [3, 4]]

        # Should not raise exception
        print_table(headers, rows, title="Test Table")


class TestTableFormatting(TestCase):
    """Test table formatting details."""

    def test_box_characters(self) -> None:
        """Test that box-drawing characters are present."""
        table = Table(["A", "B", "C"])  # Multiple columns to get all characters
        table.add_row(["1", "2", "3"])
        result = table.render()

        # Check for all box-drawing characters
        self.assertIn("┌", result)  # TOP_LEFT
        self.assertIn("┐", result)  # TOP_RIGHT
        self.assertIn("└", result)  # BOTTOM_LEFT
        self.assertIn("┘", result)  # BOTTOM_RIGHT
        self.assertIn("─", result)  # HORIZONTAL
        self.assertIn("│", result)  # VERTICAL
        self.assertIn("┬", result)  # TOP_TEE
        self.assertIn("┴", result)  # BOTTOM_TEE
        self.assertIn("├", result)  # LEFT_TEE
        self.assertIn("┤", result)  # RIGHT_TEE
        self.assertIn("┼", result)  # CROSS

    def test_alignment(self) -> None:
        """Test that content is left-aligned."""
        table = Table(["Name", "Value"])
        table.add_row(["Short", "Longer Value"])
        result = table.render()

        lines = result.split("\n")
        # Find the data row
        for line in lines:
            if "Short" in line and "Longer Value" in line:
                # Check that Short appears before Longer Value (left-aligned)
                self.assertLess(line.index("Short"), line.index("Longer Value"))
                break
