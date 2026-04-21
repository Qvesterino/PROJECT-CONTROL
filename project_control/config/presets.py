"""Project presets/templates system.

Provides pre-configured settings for different project types:
- React Frontend: JS/TS focused with Node.js conventions
- Python Backend: Python focused with Python conventions
- Full Stack: Mixed JS/TS and Python
- Custom: User-defined presets
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class PresetConfig:
    """Configuration for a project preset."""

    name: str
    description: str
    patterns: Dict[str, Any] = field(default_factory=dict)
    graph_config: Dict[str, Any] = field(default_factory=dict)
    category: str = "custom"  # builtin | custom


# ── Built-in Presets ───────────────────────────────────────────────────────

REACT_FRONTEND_PRESET = PresetConfig(
    name="react-frontend",
    description="React/Next.js frontend project (JS/TS focused)",
    category="builtin",
    patterns={
        "writers": ["scale", "emissive", "opacity", "position"],
        "entrypoints": ["index.js", "index.tsx", "main.tsx", "App.tsx"],
        "ignore_dirs": [
            ".git",
            ".project-control",
            "node_modules",
            ".next",
            "dist",
            "build",
            ".cache",
            "coverage",
        ],
        "extensions": [".js", ".jsx", ".ts", ".tsx", ".json", ".md"],
    },
    graph_config={
        "include_globs": [
            "**/*.js",
            "**/*.jsx",
            "**/*.ts",
            "**/*.tsx",
        ],
        "exclude_globs": [
            "**/node_modules/**",
            "**/.next/**",
            "**/dist/**",
            "**/build/**",
        ],
        "entrypoints": ["index.js", "index.tsx", "main.tsx", "App.tsx"],
        "alias": {
            "@/": "src/",
            "@/components/": "src/components/",
            "@/lib/": "src/lib/",
            "@/utils/": "src/utils/",
        },
        "orphan_allow_patterns": [
            "**/*.test.*",
            "**/*.spec.*",
            "**/__tests__/**",
            "**/*.stories.*",
        ],
        "treat_dynamic_imports_as_edges": True,
        "languages": {
            "js_ts": {
                "enabled": True,
                "include_exts": [".js", ".jsx", ".ts", ".tsx"],
            },
            "python": {
                "enabled": False,
                "include_exts": [".py"],
            },
        },
    },
)


PYTHON_BACKEND_PRESET = PresetConfig(
    name="python-backend",
    description="Python backend project (Django, FastAPI, Flask)",
    category="builtin",
    patterns={
        "writers": ["scale", "emissive", "opacity", "position"],
        "entrypoints": ["main.py", "app.py", "manage.py", "__init__.py"],
        "ignore_dirs": [
            ".git",
            ".project-control",
            "__pycache__",
            ".pytest_cache",
            "venv",
            "env",
            ".venv",
            "node_modules",
        ],
        "extensions": [".py", ".md", ".txt", ".yaml", ".yml"],
    },
    graph_config={
        "include_globs": [
            "**/*.py",
        ],
        "exclude_globs": [
            "**/__pycache__/**",
            "**/venv/**",
            "**/env/**",
            "**/.venv/**",
            "**/node_modules/**",
        ],
        "entrypoints": ["main.py", "app.py", "manage.py"],
        "alias": {},
        "orphan_allow_patterns": [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**",
            "**/__tests__/**",
            "**/conftest.py",
        ],
        "treat_dynamic_imports_as_edges": True,
        "languages": {
            "js_ts": {
                "enabled": False,
                "include_exts": [".js", ".jsx", ".ts", ".tsx"],
            },
            "python": {
                "enabled": True,
                "include_exts": [".py"],
            },
        },
    },
)


FULL_STACK_PRESET = PresetConfig(
    name="full-stack",
    description="Full stack project (React + Python backend)",
    category="builtin",
    patterns={
        "writers": ["scale", "emissive", "opacity", "position"],
        "entrypoints": ["index.js", "index.tsx", "main.py", "app.py"],
        "ignore_dirs": [
            ".git",
            ".project-control",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "venv",
            "env",
            ".venv",
            ".next",
            "dist",
            "build",
        ],
        "extensions": [".js", ".jsx", ".ts", ".tsx", ".py", ".json", ".md", ".yaml", ".yml"],
    },
    graph_config={
        "include_globs": [
            "**/*.js",
            "**/*.jsx",
            "**/*.ts",
            "**/*.tsx",
            "**/*.py",
        ],
        "exclude_globs": [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/env/**",
            "**/.venv/**",
            "**/.next/**",
            "**/dist/**",
            "**/build/**",
        ],
        "entrypoints": ["index.js", "index.tsx", "main.py", "app.py"],
        "alias": {
            "@/": "frontend/src/",
            "@/components/": "frontend/src/components/",
        },
        "orphan_allow_patterns": [
            "**/*.test.*",
            "**/*.spec.*",
            "**/test_*.py",
            "**/*_test.py",
            "**/__tests__/**",
            "**/tests/**",
        ],
        "treat_dynamic_imports_as_edges": True,
        "languages": {
            "js_ts": {
                "enabled": True,
                "include_exts": [".js", ".jsx", ".ts", ".tsx"],
            },
            "python": {
                "enabled": True,
                "include_exts": [".py"],
            },
        },
    },
)


BUILTIN_PRESETS: Dict[str, PresetConfig] = {
    REACT_FRONTEND_PRESET.name: REACT_FRONTEND_PRESET,
    PYTHON_BACKEND_PRESET.name: PYTHON_BACKEND_PRESET,
    FULL_STACK_PRESET.name: FULL_STACK_PRESET,
}


# ── Preset Manager ─────────────────────────────────────────────────────────

class PresetManager:
    """Manages project presets."""

    def __init__(self, project_root: Path):
        """Initialize preset manager.

        Args:
            project_root: Root path of the project
        """
        self.project_root = project_root
        self.control_dir = project_root / ".project-control"
        self.presets_dir = self.control_dir / "presets"
        self.patterns_file = self.control_dir / "patterns.yaml"
        self.graph_config_file = self.control_dir / "graph.config.yaml"

    def list_presets(self) -> List[Dict[str, str]]:
        """List all available presets.

        Returns:
            List of preset info dictionaries with name, description, category
        """
        presets = []

        # Built-in presets
        for name, preset in BUILTIN_PRESETS.items():
            presets.append({
                "name": name,
                "description": preset.description,
                "category": preset.category,
            })

        # Custom presets
        if self.presets_dir.exists():
            for preset_file in self.presets_dir.glob("*.json"):
                try:
                    data = json.loads(preset_file.read_text(encoding="utf-8"))
                    presets.append({
                        "name": data.get("name", preset_file.stem),
                        "description": data.get("description", "Custom preset"),
                        "category": "custom",
                    })
                except (json.JSONDecodeError, IOError):
                    continue

        return presets

    def get_preset(self, name: str) -> Optional[PresetConfig]:
        """Get a preset by name.

        Args:
            name: Preset name

        Returns:
            PresetConfig if found, None otherwise
        """
        # Check built-in presets
        if name in BUILTIN_PRESETS:
            return BUILTIN_PRESETS[name]

        # Check custom presets
        custom_preset_file = self.presets_dir / f"{name}.json"
        if custom_preset_file.exists():
            try:
                data = json.loads(custom_preset_file.read_text(encoding="utf-8"))
                return PresetConfig(
                    name=data.get("name", name),
                    description=data.get("description", ""),
                    patterns=data.get("patterns", {}),
                    graph_config=data.get("graph_config", {}),
                    category="custom",
                )
            except (json.JSONDecodeError, IOError):
                return None

        return None

    def apply_preset(self, name: str, backup: bool = True) -> bool:
        """Apply a preset to the project.

        Args:
            name: Preset name
            backup: If True, create backup before applying

        Returns:
            True if successful, False otherwise
        """
        preset = self.get_preset(name)
        if preset is None:
            return False

        # Create backup if requested
        if backup:
            self._create_backup()

        # Apply patterns
        if preset.patterns:
            self.control_dir.mkdir(parents=True, exist_ok=True)
            with self.patterns_file.open("w", encoding="utf-8") as f:
                yaml.dump(preset.patterns, f, default_flow_style=False, sort_keys=False)

        # Apply graph config
        if preset.graph_config:
            self.control_dir.mkdir(parents=True, exist_ok=True)
            with self.graph_config_file.open("w", encoding="utf-8") as f:
                yaml.dump(preset.graph_config, f, default_flow_style=False, sort_keys=False)

        return True

    def save_custom_preset(
        self,
        name: str,
        description: str,
        patterns: Optional[Dict[str, Any]] = None,
        graph_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a custom preset.

        Args:
            name: Preset name
            description: Preset description
            patterns: Patterns configuration (if None, use current)
            graph_config: Graph configuration (if None, use current)

        Returns:
            True if successful, False otherwise
        """
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        # Load current configs if not provided
        if patterns is None and self.patterns_file.exists():
            try:
                patterns = yaml.safe_load(self.patterns_file.read_text(encoding="utf-8"))
            except Exception:
                patterns = {}

        if graph_config is None and self.graph_config_file.exists():
            try:
                graph_config = yaml.safe_load(self.graph_config_file.read_text(encoding="utf-8"))
            except Exception:
                graph_config = {}

        preset_data = {
            "name": name,
            "description": description,
            "patterns": patterns or {},
            "graph_config": graph_config or {},
        }

        preset_file = self.presets_dir / f"{name}.json"
        preset_file.write_text(json.dumps(preset_data, indent=2), encoding="utf-8")

        return True

    def delete_custom_preset(self, name: str) -> bool:
        """Delete a custom preset.

        Args:
            name: Preset name

        Returns:
            True if deleted, False if not found or built-in
        """
        # Cannot delete built-in presets
        if name in BUILTIN_PRESETS:
            return False

        preset_file = self.presets_dir / f"{name}.json"
        if preset_file.exists():
            preset_file.unlink()
            return True

        return False

    def _create_backup(self) -> None:
        """Create backup of current configs."""
        from datetime import datetime
        backup_dir = self.control_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.patterns_file.exists():
            backup_file = backup_dir / f"patterns.yaml.{timestamp}.bak"
            import shutil
            shutil.copy2(self.patterns_file, backup_file)

        if self.graph_config_file.exists():
            backup_file = backup_dir / f"graph.config.yaml.{timestamp}.bak"
            import shutil
            shutil.copy2(self.graph_config_file, backup_file)

    def get_current_preset_name(self) -> Optional[str]:
        """Try to determine which preset matches current configuration.

        Returns:
            Preset name if match found, None otherwise
        """
        # Load current configs
        current_patterns = {}
        current_graph_config = {}

        if self.patterns_file.exists():
            try:
                current_patterns = yaml.safe_load(self.patterns_file.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        if self.graph_config_file.exists():
            try:
                current_graph_config = yaml.safe_load(self.graph_config_file.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        # Compare with built-in presets
        for name, preset in BUILTIN_PRESETS.items():
            if self._configs_match(
                current_patterns, preset.patterns,
                current_graph_config, preset.graph_config
            ):
                return name

        return None

    def _configs_match(
        self,
        patterns1: Dict[str, Any],
        patterns2: Dict[str, Any],
        graph1: Dict[str, Any],
        graph2: Dict[str, Any]
    ) -> bool:
        """Check if two configurations match (fuzzy match)."""
        # Compare key fields
        key_patterns = ["entrypoints", "ignore_dirs", "extensions"]
        for key in key_patterns:
            if patterns1.get(key) != patterns2.get(key):
                return False

        # Compare graph language settings
        lang1 = graph1.get("languages", {})
        lang2 = graph2.get("languages", {})

        for lang_name in ["js_ts", "python"]:
            if lang1.get(lang_name, {}).get("enabled") != lang2.get(lang_name, {}).get("enabled"):
                return False

        return True
