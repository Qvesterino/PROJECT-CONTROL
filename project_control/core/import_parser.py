import re
from typing import List

IMPORT_FROM_RE = re.compile(r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]')
IMPORT_ONLY_RE = re.compile(r'import\s+[\'"](.+?)[\'"]')
REQUIRE_RE = re.compile(r'require\(\s*[\'"](.+?)[\'"]\s*\)')


def extract_imports(content: str) -> List[str]:
    """
    Extract static import paths from JS/TS file content.
    Supports:
        - import ... from "..."
        - import "..."
        - require("...")
    Ignores dynamic imports.
    """
    imports = []

    imports.extend(IMPORT_FROM_RE.findall(content))
    imports.extend(IMPORT_ONLY_RE.findall(content))
    imports.extend(REQUIRE_RE.findall(content))

    return imports