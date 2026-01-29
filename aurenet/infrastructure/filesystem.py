"""
AURENET - Filesystem Abstraction

Provides abstraction layer for file I/O operations.
This allows mocking in tests and makes the code more testable.
"""

import os
from typing import Protocol


class FileSystemAdapter(Protocol):
    """Protocol for filesystem operations."""

    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        ...

    def read(self, path: str) -> str:
        """Read file contents as string."""
        ...

    def write(self, path: str, content: str) -> None:
        """Write string content to file."""
        ...

    def delete(self, path: str) -> None:
        """Delete a file."""
        ...


class RealFileSystem:
    """Real filesystem implementation."""

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def read(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def write(self, path: str, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    def delete(self, path: str) -> None:
        if self.exists(path):
            os.remove(path)


class MockFileSystem:
    """Mock filesystem for testing."""

    def __init__(self):
        self._files: dict[str, str] = {}

    def exists(self, path: str) -> bool:
        return path in self._files

    def read(self, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path]

    def write(self, path: str, content: str) -> None:
        self._files[path] = content

    def delete(self, path: str) -> None:
        if path in self._files:
            del self._files[path]
