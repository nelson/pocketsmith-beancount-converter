"""File and directory handling utilities for CLI commands."""

import os
from pathlib import Path
from typing import Union


class FileHandlerError(Exception):
    """Raised when file handling operations fail."""

    pass


def validate_output_destination(
    destination: Union[str, Path], single_file: bool = False
) -> Path:
    """Validate and prepare output destination.

    Args:
        destination: Output destination path
        single_file: Whether this is for single file output

    Returns:
        Validated Path object

    Raises:
        FileHandlerError: If destination is invalid
    """
    dest_path = Path(destination)

    # Check if destination already exists
    try:
        if dest_path.exists():
            if single_file:
                raise FileHandlerError(f"File '{dest_path}' already exists")
            else:
                raise FileHandlerError(f"Directory '{dest_path}' already exists")
    except PermissionError:
        # If we can't even check if the path exists due to permissions, that's an error
        raise FileHandlerError(f"Permission denied accessing '{dest_path}'")

    # Check if parent directory exists and is writable
    parent_dir = dest_path.parent
    if not parent_dir.exists():
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileHandlerError(
                f"Cannot create parent directory '{parent_dir}': {e}"
            )

    if not os.access(parent_dir, os.W_OK):
        raise FileHandlerError(f"Parent directory '{parent_dir}' is not writable")

    return dest_path


def ensure_beancount_extension(file_path: Path) -> Path:
    """Ensure file path has .beancount extension.

    Args:
        file_path: File path to check

    Returns:
        Path with .beancount extension
    """
    # Handle edge cases with empty or dot-only paths
    if not file_path.name or file_path.name == ".":
        return Path(".beancount")

    if file_path.suffix != ".beancount":
        return file_path.with_suffix(".beancount")
    return file_path


def create_hierarchical_structure(base_dir: Path) -> None:
    """Create hierarchical directory structure for beancount files.

    Args:
        base_dir: Base directory to create structure in

    Raises:
        FileHandlerError: If directory creation fails
    """
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise FileHandlerError(f"Cannot create directory '{base_dir}': {e}")


def get_output_file_path(destination: Path, single_file: bool) -> Path:
    """Get the final output file path.

    Args:
        destination: Destination path from user
        single_file: Whether single file mode is enabled

    Returns:
        Final output file path
    """
    if single_file:
        return ensure_beancount_extension(destination)
    else:
        # For hierarchical mode, main file is in the destination directory
        return destination / "main.beancount"
