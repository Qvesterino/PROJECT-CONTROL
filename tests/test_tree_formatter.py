"""Tests for ASCII tree formatter."""

from __future__ import annotations

from project_control.utils.tree_formatter import format_file_tree, TreeFormatter


def test_basic_tree():
    """Test basic tree formatting."""
    files = [
        "src/main.py",
        "src/utils/helpers.py",
        "tests/test_main.py",
        "README.md"
    ]
    
    result = format_file_tree(files, root_label=".")
    
    assert "." in result
    assert "src" in result
    assert "tests" in result
    assert "main.py" in result
    assert "helpers.py" in result
    assert "test_main.py" in result
    assert "README.md" in result
    
    # Check for tree connectors
    assert "+---" in result or "\\---" in result
    print("Basic tree test passed!")
    print(result)


def test_empty_tree():
    """Test empty tree formatting."""
    result = format_file_tree([])
    
    assert "." in result
    assert "empty" in result.lower()
    print("Empty tree test passed!")
    print(result)


def test_show_counts():
    """Test showing item counts in tree."""
    files = [
        "src/main.py",
        "src/utils.py",
        "src/helpers.py"
    ]
    
    result = format_file_tree(files, show_counts=True)
    
    assert "items" in result
    print("Show counts test passed!")
    print(result)


def test_tree_formatter_class():
    """Test TreeFormatter class directly."""
    formatter = TreeFormatter(root_label="project")
    
    files = [
        "lib/core.py",
        "lib/utils/str.py",
        "lib/utils/num.py",
        "README.md"
    ]
    
    result = formatter.format(files, show_counts=False)
    
    assert "project" in result
    assert "lib" in result
    assert "core.py" in result
    print("TreeFormatter class test passed!")
    print(result)


if __name__ == "__main__":
    test_basic_tree()
    print("\n" + "="*60 + "\n")
    test_empty_tree()
    print("\n" + "="*60 + "\n")
    test_show_counts()
    print("\n" + "="*60 + "\n")
    test_tree_formatter_class()
    print("\n" + "="*60)
    print("All tests passed! ✅")