from typing import Any, Dict, List

def detect_session_files(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
    """
    Return any files whose names include 'session' (case-insensitive).
    """
    results: List[str] = []

    for file in snapshot.get("files", []):
        path = file.get("path", "")
        if "session" in path.lower():
            results.append(path)

    return results
