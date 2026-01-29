"""
AURENET - Trigger File System

Handles reading and clearing trigger files used for developer notifications.
"""

from typing import Optional
from .filesystem import FileSystemAdapter


class TriggerFileSystem:
    """Manages trigger files for developer notifications."""

    def __init__(self, fs: FileSystemAdapter, trigger_dir: str = "/tmp"):
        self._fs = fs
        self._trigger_dir = trigger_dir

    def check_trigger(self, name: str) -> Optional[str]:
        """
        Check if a trigger file exists and return its content.

        Args:
            name: Name of the trigger (e.g., 'task_complete')

        Returns:
            File content if exists, None otherwise
        """
        trigger_path = f"{self._trigger_dir}/aurenet_{name}.txt"

        if self._fs.exists(trigger_path):
            try:
                content = self._fs.read(trigger_path)
                return content.strip()
            except Exception:
                return None

        return None

    def clear_trigger(self, name: str) -> None:
        """
        Clear (delete) a trigger file.

        Args:
            name: Name of the trigger (e.g., 'task_complete')
        """
        trigger_path = f"{self._trigger_dir}/aurenet_{name}.txt"
        try:
            self._fs.delete(trigger_path)
        except Exception:
            pass  # Silently ignore deletion errors

    def check_and_clear(self, name: str) -> bool:
        """
        Check if trigger exists and clear it in one operation.

        Args:
            name: Name of the trigger (e.g., 'task_complete')

        Returns:
            True if trigger was found, False otherwise
        """
        content = self.check_trigger(name)
        if content is not None:
            self.clear_trigger(name)
            return True
        return False
