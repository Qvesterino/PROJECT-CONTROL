"""Render layer for CLI output formatting."""

from __future__ import annotations

from project_control.utils.terminal import Colors


def render_dead(result: dict, colored: bool = True) -> str:
    """
    Render dead code analysis result.

    Args:
        result: DeadCodeResult from dead_analyzer.
        colored: If True, use colored output (default: True).

    Returns:
        Formatted string output.
    """
    lines = []

    # Title
    if colored:
        lines.append(f"{Colors.BOLD}{Colors.BLUE}Dead Code Radar{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'=' * 50}{Colors.RESET}")
    else:
        lines.append("Dead Code Radar")
        lines.append("=" * 50)

    high = result.get("high", [])
    medium = result.get("medium", [])
    stats = result.get("stats", {})

    # HIGH section
    if colored:
        lines.append(f"\n{Colors.BOLD}{Colors.RED}HIGH (Orphan Files){Colors.RESET}: {len(high)}")
    else:
        lines.append(f"\nHIGH (Orphan Files): {len(high)}")

    if high:
        for item in high:
            if colored:
                lines.append(f"  {Colors.RED}*{Colors.RESET} {item['file']} {Colors.DIM}(usage: {item['usage']}){Colors.RESET}")
            else:
                lines.append(f"  * {item['file']} (usage: {item['usage']})")
    else:
        if colored:
            lines.append(f"  {Colors.GREEN}*{Colors.RESET} None found")
        else:
            lines.append("  * None found")

    # MEDIUM section
    if colored:
        lines.append(f"\n{Colors.BOLD}{Colors.YELLOW}MEDIUM (Low Usage){Colors.RESET}: {len(medium)}")
    else:
        lines.append(f"\nMEDIUM (Low Usage): {len(medium)}")

    if medium:
        for item in medium:
            if colored:
                lines.append(f"  {Colors.YELLOW}*{Colors.RESET} {item['file']} {Colors.DIM}(usage: {item['usage']}){Colors.RESET}")
            else:
                lines.append(f"  * {item['file']} (usage: {item['usage']})")
    else:
        if colored:
            lines.append(f"  {Colors.GREEN}*{Colors.RESET} None found")
        else:
            lines.append("  * None found")

    # Stats
    if colored:
        lines.append(f"\n{Colors.DIM}{'-' * 50}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Total files:{Colors.RESET} {stats.get('total_files', 0)}")
        lines.append(f"{Colors.RED}Dead files:{Colors.RESET} {stats.get('dead_files', 0)}")
        lines.append(f"{Colors.YELLOW}Low usage files:{Colors.RESET} {stats.get('low_usage_files', 0)}")
    else:
        lines.append("\n" + "-" * 50)
        lines.append(f"Total files: {stats.get('total_files', 0)}")
        lines.append(f"Dead files: {stats.get('dead_files', 0)}")
        lines.append(f"Low usage files: {stats.get('low_usage_files', 0)}")

    return "\n".join(lines)


def render_unused(result: dict, colored: bool = True) -> str:
    """
    Render unused systems analysis result.

    Args:
        result: UnusedSystemsResult from unused_analyzer.
        colored: If True, use colored output (default: True).

    Returns:
        Formatted string output.
    """
    lines = []

    # Title
    if colored:
        lines.append(f"{Colors.BOLD}{Colors.BLUE}Unused Systems Scan{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'=' * 50}{Colors.RESET}")
    else:
        lines.append("Unused Systems Scan")
        lines.append("=" * 50)

    unused = result.get("unused_systems", [])
    stats = result.get("stats", {})

    # Unused systems section
    if colored:
        lines.append(f"\n{Colors.BOLD}{Colors.YELLOW}Unused Systems{Colors.RESET}: {len(unused)}")
    else:
        lines.append(f"\nUnused Systems: {len(unused)}")

    if unused:
        for item in unused:
            if colored:
                lines.append(f"  {Colors.YELLOW}*{Colors.RESET} {item['file']}")
                lines.append(f"    {Colors.DIM}System:{Colors.RESET} {item['system_name']}")
            else:
                lines.append(f"  * {item['file']}")
                lines.append(f"    System: {item['system_name']}")
    else:
        if colored:
            lines.append(f"  {Colors.GREEN}*{Colors.RESET} No unused systems found")
        else:
            lines.append("  * No unused systems found")

    # Stats
    if colored:
        lines.append(f"\n{Colors.DIM}{'-' * 50}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Total systems:{Colors.RESET} {stats.get('total_systems', 0)}")
        lines.append(f"{Colors.YELLOW}Unused count:{Colors.RESET} {stats.get('unused_count', 0)}")
    else:
        lines.append("\n" + "-" * 50)
        lines.append(f"Total systems: {stats.get('total_systems', 0)}")
        lines.append(f"Unused count: {stats.get('unused_count', 0)}")

    return "\n".join(lines)


def render_patterns(result: dict, colored: bool = True) -> str:
    """
    Render patterns analysis result.

    Args:
        result: PatternsResult from patterns_analyzer.
        colored: If True, use colored output (default: True).

    Returns:
        Formatted string output.
    """
    lines = []

    # Title
    if colored:
        lines.append(f"{Colors.BOLD}{Colors.BLUE}Suspicious Patterns{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'=' * 50}{Colors.RESET}")
    else:
        lines.append("Suspicious Patterns")
        lines.append("=" * 50)

    patterns = result.get("patterns", {})
    stats = result.get("stats", {})

    for pattern_name, pattern_data in patterns.items():
        matches = pattern_data.get("matches", [])

        if colored:
            lines.append(f"\n{Colors.BOLD}{Colors.MAGENTA}Pattern:{Colors.RESET} {pattern_name} {Colors.DIM}({len(matches)} matches){Colors.RESET}")
        else:
            lines.append(f"\nPattern: {pattern_name} ({len(matches)} matches)")

        if matches:
            # Show first 10 matches
            for match in matches[:10]:
                if colored:
                    lines.append(f"  {Colors.RED}*{Colors.RESET} {match['file']}:{Colors.CYAN}{match['line']}{Colors.RESET}")
                    lines.append(f"    {Colors.DIM}{match['text'][:80]}{Colors.RESET}")
                else:
                    lines.append(f"  * {match['file']}:{match['line']}")
                    lines.append(f"    {match['text'][:80]}")

            if len(matches) > 10:
                if colored:
                    lines.append(f"  {Colors.DIM}... and {len(matches) - 10} more{Colors.RESET}")
                else:
                    lines.append(f"  ... and {len(matches) - 10} more")
        else:
            if colored:
                lines.append(f"  {Colors.GREEN}*{Colors.RESET} No matches")
            else:
                lines.append("  * No matches")

    # Stats
    if colored:
        lines.append(f"\n{Colors.DIM}{'-' * 50}{Colors.RESET}")
        lines.append(f"{Colors.CYAN}Total patterns checked:{Colors.RESET} {stats.get('total_patterns', 0)}")
        lines.append(f"{Colors.YELLOW}Patterns with matches:{Colors.RESET} {stats.get('matched_patterns', 0)}")
        lines.append(f"{Colors.MAGENTA}Total matches:{Colors.RESET} {stats.get('total_matches', 0)}")
    else:
        lines.append("\n" + "-" * 50)
        lines.append(f"Total patterns checked: {stats.get('total_patterns', 0)}")
        lines.append(f"Patterns with matches: {stats.get('matched_patterns', 0)}")
        lines.append(f"Total matches: {stats.get('total_matches', 0)}")

    return "\n".join(lines)


def render_search(result: dict, colored: bool = True) -> str:
    """
    Render smart search result.

    Args:
        result: SearchResult from search_analyzer.
        colored: If True, use colored output (default: True).

    Returns:
        Formatted string output.
    """
    lines = []

    # Title
    if colored:
        lines.append(f"{Colors.BOLD}{Colors.BLUE}Search Results{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'=' * 50}{Colors.RESET}")
    else:
        lines.append("Search Results")
        lines.append("=" * 50)

    matches = result.get("matches", [])
    stats = result.get("stats", {})

    # Results count
    if colored:
        lines.append(f"\n{Colors.GREEN}Found {len(matches)} result(s){Colors.RESET}")
    else:
        lines.append(f"\nFound {len(matches)} result(s)")

    if matches:
        files_only = stats.get("files_only", False)
        if files_only:
            for match in matches:
                if colored:
                    lines.append(f"  {Colors.CYAN}*{Colors.RESET} {match['file']}")
                else:
                    lines.append(f"  * {match['file']}")
        else:
            for match in matches:
                if colored:
                    lines.append(f"  {Colors.CYAN}*{Colors.RESET} {match['file']}:{Colors.YELLOW}{match['line']}{Colors.RESET}")
                    lines.append(f"    {Colors.DIM}{match['text']}{Colors.RESET}")
                else:
                    lines.append(f"  * {match['file']}:{match['line']}")
                    lines.append(f"    {match['text']}")
    else:
        if colored:
            lines.append(f"  {Colors.YELLOW}No results found{Colors.RESET}")
        else:
            lines.append("  * No results found")

    return "\n".join(lines)
