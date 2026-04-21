"""Consolidated state management for PROJECT_CONTROL.

This module provides unified state management, replacing the separate
config.json and status.yaml files with a single state.json file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UIState:
    """User interface state (from old config.json)."""
    project_mode: str = "js_ts"  # js_ts | python | mixed
    graph_profile: str = "pragmatic"  # pragmatic | strict
    trace_direction: str = "both"  # inbound | outbound | both
    trace_depth: int = 50
    trace_all_paths: bool = False


@dataclass
class TagState:
    """Tag state (from old status.yaml)."""
    tags: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class UserPreferences:
    """User preferences and frequently used items."""
    favorites: List[str] = field(default_factory=list)  # Frequently traced targets
    history: List[str] = field(default_factory=list)  # Recent actions (last 10)


@dataclass
class ProjectMetadata:
    """Project metadata and timestamps."""
    last_scan: Optional[str] = None  # ISO format timestamp
    last_graph_build: Optional[str] = None  # ISO format timestamp
    last_analysis: Optional[str] = None  # ISO format timestamp
    project_root: Optional[str] = None  # Project root path


@dataclass
class AppState:
    """Consolidated application state.

    This replaces the separate config.json and status.yaml files
    with a single state.json file containing all state.
    """
    ui: UIState = field(default_factory=UIState)
    tags: TagState = field(default_factory=TagState)
    user: UserPreferences = field(default_factory=UserPreferences)
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    version: str = "1.0"  # State format version

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "ui": asdict(self.ui),
            "tags": asdict(self.tags),
            "user": asdict(self.user),
            "metadata": asdict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppState":
        """Create AppState from dictionary."""
        version = data.get("version", "1.0")

        ui_data = data.get("ui", {})
        ui = UIState(
            project_mode=ui_data.get("project_mode", "js_ts"),
            graph_profile=ui_data.get("graph_profile", "pragmatic"),
            trace_direction=ui_data.get("trace_direction", "both"),
            trace_depth=ui_data.get("trace_depth", 50),
            trace_all_paths=ui_data.get("trace_all_paths", False),
        )

        tags_data = data.get("tags", {})
        tags = TagState(tags=tags_data.get("tags", {}))

        user_data = data.get("user", {})
        user = UserPreferences(
            favorites=user_data.get("favorites", []),
            history=user_data.get("history", []),
        )

        metadata_data = data.get("metadata", {})
        metadata = ProjectMetadata(
            last_scan=metadata_data.get("last_scan"),
            last_graph_build=metadata_data.get("last_graph_build"),
            last_analysis=metadata_data.get("last_analysis"),
            project_root=metadata_data.get("project_root"),
        )

        return cls(version=version, ui=ui, tags=tags, user=user, metadata=metadata)


class StateManager:
    """Manages loading, saving, and migrating application state."""

    STATE_FILE = "state.json"
    OLD_CONFIG_FILE = "config.json"
    OLD_STATUS_FILE = "status.yaml"

    def __init__(self, project_root: Path):
        """Initialize state manager.

        Args:
            project_root: Root path of the project
        """
        self.project_root = project_root
        self.control_dir = project_root / ".project-control"
        self.state_path = self.control_dir / self.STATE_FILE
        self.old_config_path = self.control_dir / self.OLD_CONFIG_FILE
        self.old_status_path = self.control_dir / self.OLD_STATUS_FILE

    def load(self) -> AppState:
        """Load application state.

        Returns:
            AppState instance

        If state.json doesn't exist, will attempt to migrate from
        old config.json and status.yaml files.
        """
        if self.state_path.exists():
            return self._load_state_file()

        # Try to migrate from old files
        if self.old_config_path.exists() or self.old_status_path.exists():
            state = self._migrate_from_old_files()
            self.save(state)
            return state

        # Return default state
        return AppState()

    def _load_state_file(self) -> AppState:
        """Load state from state.json."""
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return AppState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # If file is corrupted, return default state
            import logging
            logging.warning(f"Failed to load state file, using defaults: {e}")
            return AppState()

    def _migrate_from_old_files(self) -> AppState:
        """Migrate state from old config.json and status.yaml files."""
        state = AppState()

        # Migrate from old config.json
        if self.old_config_path.exists():
            try:
                config_data = json.loads(self.old_config_path.read_text(encoding="utf-8"))
                state.ui = UIState(
                    project_mode=config_data.get("project_mode", "js_ts"),
                    graph_profile=config_data.get("graph_profile", "pragmatic"),
                    trace_direction=config_data.get("trace_direction", "both"),
                    trace_depth=config_data.get("trace_depth", 50),
                    trace_all_paths=config_data.get("trace_all_paths", False),
                )
                state.user.favorites = config_data.get("favorites", [])
                state.user.history = config_data.get("history", [])
            except (json.JSONDecodeError, IOError) as e:
                import logging
                logging.warning(f"Failed to migrate config.json: {e}")

        # Migrate from old status.yaml
        if self.old_status_path.exists():
            try:
                import yaml
                status_data = yaml.safe_load(self.old_status_path.read_text(encoding="utf-8"))
                if status_data:
                    state.tags = TagState(tags=status_data.get("tags", {}))
            except Exception as e:
                import logging
                logging.warning(f"Failed to migrate status.yaml: {e}")

        return state

    def save(self, state: AppState) -> None:
        """Save application state to state.json.

        Args:
            state: AppState instance to save
        """
        self.control_dir.mkdir(parents=True, exist_ok=True)

        data = state.to_dict()
        self.state_path.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8"
        )

    def update_last_scan(self) -> None:
        """Update the last scan timestamp."""
        state = self.load()
        state.metadata.last_scan = datetime.now().isoformat()
        state.metadata.project_root = str(self.project_root)
        self.save(state)

    def update_last_graph_build(self) -> None:
        """Update the last graph build timestamp."""
        state = self.load()
        state.metadata.last_graph_build = datetime.now().isoformat()
        state.metadata.project_root = str(self.project_root)
        self.save(state)

    def update_last_analysis(self) -> None:
        """Update the last analysis timestamp."""
        state = self.load()
        state.metadata.last_analysis = datetime.now().isoformat()
        self.save(state)

    def add_to_history(self, action: str, max_history: int = 10) -> None:
        """Add action to history.

        Args:
            action: Action description to add
            max_history: Maximum number of history items to keep
        """
        state = self.load()
        state.user.history = [action] + state.user.history[:max_history - 1]
        self.save(state)

    def add_to_favorites(self, target: str) -> None:
        """Add target to favorites if not already present.

        Args:
            target: Target path to add
        """
        state = self.load()
        if target not in state.user.favorites:
            state.user.favorites.append(target)
            self.save(state)

    def remove_from_favorites(self, target: str) -> None:
        """Remove target from favorites.

        Args:
            target: Target path to remove
        """
        state = self.load()
        state.user.favorites = [f for f in state.user.favorites if f != target]
        self.save(state)

    def get_tags(self) -> Dict[str, List[str]]:
        """Get all tags.

        Returns:
            Dictionary mapping tag names to lists of file paths
        """
        state = self.load()
        return state.tags.tags

    def set_tags(self, tags: Dict[str, List[str]]) -> None:
        """Set all tags.

        Args:
            tags: Dictionary mapping tag names to lists of file paths
        """
        state = self.load()
        state.tags.tags = tags
        self.save(state)

    def add_file_to_tag(self, tag: str, file_path: str) -> None:
        """Add a file to a tag.

        Args:
            tag: Tag name
            file_path: File path to add
        """
        state = self.load()
        if tag not in state.tags.tags:
            state.tags.tags[tag] = []
        if file_path not in state.tags.tags[tag]:
            state.tags.tags[tag].append(file_path)
        self.save(state)

    def remove_file_from_tag(self, tag: str, file_path: str) -> None:
        """Remove a file from a tag.

        Args:
            tag: Tag name
            file_path: File path to remove
        """
        state = self.load()
        if tag in state.tags.tags:
            state.tags.tags[tag] = [f for f in state.tags.tags[tag] if f != file_path]
            if not state.tags.tags[tag]:
                del state.tags.tags[tag]
            self.save(state)

    def cleanup_old_files(self, backup: bool = True) -> None:
        """Remove old state files (config.json, status.yaml).

        Args:
            backup: If True, create backups before deleting
        """
        import logging
        logger = logging.getLogger(__name__)

        if backup:
            from datetime import datetime
            backup_dir = self.control_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for old_file in [self.old_config_path, self.old_status_path]:
                if old_file.exists():
                    backup_path = backup_dir / f"{old_file.name}.{timestamp}.bak"
                    old_file.rename(backup_path)
                    logger.info(f"Backed up {old_file.name} to {backup_path}")

        # Delete old files
        for old_file in [self.old_config_path, self.old_status_path]:
            if old_file.exists():
                old_file.unlink()
                logger.info(f"Removed old state file: {old_file.name}")

    def export_state(self, export_path: Optional[Path] = None, include_metadata: bool = True) -> Path:
        """Export state to a file.

        Args:
            export_path: Path to export to. If None, uses default path.
            include_metadata: Whether to include project metadata (project_root, timestamps)

        Returns:
            Path to the exported file
        """
        if export_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = self.control_dir / "exports" / f"state.{timestamp}.json"

        export_path.parent.mkdir(parents=True, exist_ok=True)

        state = self.load()

        # Create export data
        export_data = {
            "version": state.version,
            "ui": state.ui.__dict__,
            "tags": state.tags.__dict__,
            "user": state.user.__dict__,
        }

        # Optionally exclude project-specific metadata for portability
        if include_metadata:
            export_data["metadata"] = {
                "last_scan": state.metadata.last_scan,
                "last_graph_build": state.metadata.last_graph_build,
                "last_analysis": state.metadata.last_analysis,
                # Exclude project_root for portability
            }

        export_path.write_text(
            json.dumps(export_data, indent=2, sort_keys=True),
            encoding="utf-8"
        )

        return export_path

    def import_state(self, import_path: Path, merge: bool = False) -> None:
        """Import state from a file.

        Args:
            import_path: Path to the state file to import
            merge: If True, merge with existing state. If False, replace entirely.
        """
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")

        import_data = json.loads(import_path.read_text(encoding="utf-8"))

        if merge:
            # Load current state and merge
            current_state = self.load()

            # Merge UI settings (import takes precedence)
            if "ui" in import_data:
                current_state.ui = UIState(**import_data["ui"])

            # Merge tags (import takes precedence)
            if "tags" in import_data:
                current_state.tags = TagState(**import_data["tags"])

            # Merge user preferences (combine favorites and history)
            if "user" in import_data:
                user_data = import_data["user"]
                if "favorites" in user_data:
                    # Combine favorites, avoid duplicates
                    for fav in user_data["favorites"]:
                        if fav not in current_state.user.favorites:
                            current_state.user.favorites.append(fav)
                if "history" in user_data:
                    # Prepend import history
                    current_state.user.history = user_data["history"] + current_state.user.history
                    # Keep only last 10
                    current_state.user.history = current_state.user.history[:10]

            self.save(current_state)
        else:
            # Replace entirely
            state = AppState.from_dict(import_data)
            self.save(state)
