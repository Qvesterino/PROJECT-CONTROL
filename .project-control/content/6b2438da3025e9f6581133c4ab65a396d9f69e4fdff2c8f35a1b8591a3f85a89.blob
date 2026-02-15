from project_control.config.patterns_loader import load_patterns
from project_control.utils.fs_helpers import run_rg


def run_writers_analysis(project_root):
    patterns = load_patterns(project_root)
    writer_patterns = patterns.get("writers", [])

    results = {}

    for pattern in writer_patterns:
        output = run_rg(pattern)
        results[pattern] = output.strip() if output else ""

    return results
