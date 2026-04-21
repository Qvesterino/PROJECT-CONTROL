"""Backup and rollback management for PROJECT_CONTROL."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from project_control.core.error_handler import OperationError, FileNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class Backup:
    """Represents a backup with metadata."""

    name: str
    timestamp: str
    path: Path
    size_bytes: int
    description: Optional[str] = None

    def __str__(self) -> str:
        size_mb = self.size_bytes / (1024 * 1024)
        time_str = datetime.fromisoformat(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return f"{self.name} ({time_str}, {size_mb:.2f} MB)"


class BackupManager:
    """
    Manage .project-control backups with automatic cleanup and restoration.

    Backups are stored in .project-control/backups/ and contain complete
    copies of the .project-control directory at the time of backup.
    """

    def __init__(self, project_root: Path):
        """
        Initialize backup manager.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.control_dir = self.project_root / ".project-control"
        self.backup_dir = self.control_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.backup_dir / "metadata.json"

    def create_backup(self, name: Optional[str] = None, description: Optional[str] = None) -> Backup:
        """
        Create a timestamped backup of .project-control directory.

        Args:
            name: Optional custom name for backup (defaults to timestamp)
            description: Optional description of what this backup is for

        Returns:
            Backup object with metadata

        Raises:
            FileNotFoundError: If .project-control directory doesn't exist
            OperationError: If backup creation fails
        """
        if not self.control_dir.exists():
            raise FileNotFoundError(
                "Project control directory not found",
                details=f"Expected: {self.control_dir}"
            )

        # Generate backup name
        timestamp = datetime.now()
        timestamp_str = timestamp.isoformat()
        backup_name = name if name else f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Create backup directory
        backup_path = self.backup_dir / backup_name
        if backup_path.exists():
            logger.warning(f"Backup directory already exists: {backup_path}, will replace")
            shutil.rmtree(backup_path)

        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy all files except existing backups
        try:
            for item in self.control_dir.iterdir():
                if item.name == "backups" or item == self.backup_dir:
                    continue  # Skip backup directory itself
                if item.is_file():
                    shutil.copy2(item, backup_path / item.name)
                elif item.is_dir():
                    shutil.copytree(item, backup_path / item.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        except Exception as e:
            # Clean up failed backup attempt
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise OperationError(
                "Failed to create backup",
                details=str(e)
            )

        # Calculate size
        size_bytes = self._calculate_directory_size(backup_path)

        # Create backup metadata
        backup = Backup(
            name=backup_name,
            timestamp=timestamp_str,
            path=backup_path,
            size_bytes=size_bytes,
            description=description
        )

        # Save metadata
        self._save_backup_metadata(backup)

        logger.info(f"Backup created: {backup_name} at {backup_path}")
        return backup

    def list_backups(self) -> list[Backup]:
        """
        List all available backups.

        Returns:
            List of Backup objects, sorted by timestamp (newest first)
        """
        backups = []

        # Load metadata file if exists
        metadata = self._load_metadata()

        if not self.backup_dir.exists():
            return backups

        for backup_path in self.backup_dir.iterdir():
            if not backup_path.is_dir():
                continue

            backup_name = backup_path.name
            backup_meta = metadata.get(backup_name, {})

            # Get timestamp from metadata or directory mtime
            timestamp = backup_meta.get("timestamp")
            if not timestamp:
                # Fallback to directory modification time
                mtime = backup_path.stat().st_mtime
                timestamp = datetime.fromtimestamp(mtime).isoformat()

            size_bytes = self._calculate_directory_size(backup_path)

            backup = Backup(
                name=backup_name,
                timestamp=timestamp,
                path=backup_path,
                size_bytes=size_bytes,
                description=backup_meta.get("description")
            )

            backups.append(backup)

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    def restore_backup(self, backup: Backup, confirm: bool = True) -> None:
        """
        Restore project state from a backup.

        Args:
            backup: Backup object to restore
            confirm: If True, require user confirmation (for CLI use)

        Raises:
            FileNotFoundError: If backup directory doesn't exist
            OperationError: If restore fails
        """
        if not backup.path.exists():
            raise FileNotFoundError(
                "Backup directory not found",
                details=f"Backup path: {backup.path}"
            )

        if confirm:
            response = input(f"\n⚠️  Restore from '{backup.name}'? This will replace current .project-control/ (y/N): ").strip()
            if response.lower() != "y":
                print("Restore cancelled.")
                return

        try:
            # Create emergency backup of current state
            emergency_backup_name = f"emergency_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                self.create_backup(name=emergency_backup_name, description="Emergency backup before restore")
                logger.info(f"Emergency backup created: {emergency_backup_name}")
            except Exception as e:
                logger.warning(f"Could not create emergency backup: {e}")

            # Remove current .project-control contents (except backups)
            for item in self.control_dir.iterdir():
                if item == self.backup_dir or item.is_symlink() and item.resolve() == self.backup_dir:
                    continue  # Don't remove backup directory
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            # Restore from backup
            for item in backup.path.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.control_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, self.control_dir / item.name)

            logger.info(f"Successfully restored from backup: {backup.name}")
            print(f"\n✅ Restored from backup: {backup.name}")

        except Exception as e:
            raise OperationError(
                "Failed to restore backup",
                details=str(e)
            )

    def delete_backup(self, backup: Backup) -> None:
        """
        Delete a specific backup.

        Args:
            backup: Backup object to delete

        Raises:
            FileNotFoundError: If backup doesn't exist
            OperationError: If deletion fails
        """
        if not backup.path.exists():
            raise FileNotFoundError(
                "Backup directory not found",
                details=f"Backup path: {backup.path}"
            )

        try:
            shutil.rmtree(backup.path)
            self._remove_backup_metadata(backup.name)
            logger.info(f"Backup deleted: {backup.name}")
        except Exception as e:
            raise OperationError(
                "Failed to delete backup",
                details=str(e)
            )

    def cleanup_old_backups(self, keep: int = 5) -> int:
        """
        Remove old backups, keeping only the most recent ones.

        Args:
            keep: Number of most recent backups to keep

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep:
            logger.info(f"Only {len(backups)} backups exist, keeping all (limit: {keep})")
            return 0

        # Remove excess backups (keep newest N)
        to_delete = backups[keep:]
        deleted_count = 0

        for backup in to_delete:
            try:
                self.delete_backup(backup)
                deleted_count += 1
                logger.info(f"Deleted old backup: {backup.name}")
            except Exception as e:
                logger.error(f"Failed to delete backup {backup.name}: {e}")

        return deleted_count

    def get_latest_backup(self) -> Optional[Backup]:
        """
        Get the most recent backup.

        Returns:
            Backup object or None if no backups exist
        """
        backups = self.list_backups()
        return backups[0] if backups else None

    # ── Private helpers ───────────────────────────────────────────────

    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of a directory in bytes."""
        total_size = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except (OSError, PermissionError):
            pass  # Skip files we can't read
        return total_size

    def _load_metadata(self) -> dict:
        """Load backup metadata from JSON file."""
        if not self._metadata_file.exists():
            return {}

        try:
            return json.loads(self._metadata_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load backup metadata: {e}")
            return {}

    def _save_backup_metadata(self, backup: Backup) -> None:
        """Save backup metadata to JSON file."""
        metadata = self._load_metadata()

        metadata[backup.name] = {
            "timestamp": backup.timestamp,
            "description": backup.description,
            "size_bytes": backup.size_bytes
        }

        try:
            self._metadata_file.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except (IOError, OSError) as e:
            logger.warning(f"Could not save backup metadata: {e}")

    def _remove_backup_metadata(self, backup_name: str) -> None:
        """Remove backup metadata from JSON file."""
        metadata = self._load_metadata()

        if backup_name in metadata:
            del metadata[backup_name]

            try:
                self._metadata_file.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
            except (IOError, OSError) as e:
                logger.warning(f"Could not update backup metadata: {e}")


# ── Context Manager for automatic backup ─────────────────────────────

class BackupContext:
    """
    Context manager for automatic backup before destructive operations.

    Usage:
        with BackupContext(project_root, "before_rebuild"):
            # Perform destructive operation
            rebuild_graph()
            # If exception occurs, backup is preserved for recovery
    """

    def __init__(self, project_root: Path, operation_name: str, auto_cleanup: bool = True):
        self.project_root = project_root
        self.operation_name = operation_name
        self.auto_cleanup = auto_cleanup
        self.backup_manager = None
        self.backup = None

    def __enter__(self) -> BackupManager:
        self.backup_manager = BackupManager(self.project_root)
        self.backup = self.backup_manager.create_backup(
            name=f"auto_{self.operation_name}",
            description=f"Automatic backup before: {self.operation_name}"
        )
        logger.info(f"Created automatic backup: {self.backup.name}")
        print(f"[Backup] Created: {self.backup.name}")
        return self.backup_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Operation failed, backup is available for recovery
            print(f"\n[Warning] Operation failed. Backup available: {self.backup.name}")
            print(f"   To restore: use Tools -> Restore Backup")
            return False

        # Operation succeeded, optionally cleanup old backups
        if self.auto_cleanup:
            deleted = self.backup_manager.cleanup_old_backups(keep=5)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old backups")

        return False
