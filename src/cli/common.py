"""Common CLI utilities and shared functionality."""

import typer
from pathlib import Path
from typing import Optional, Any

from .file_handler import find_default_beancount_file, FileHandlerError


def handle_default_destination(destination: Optional[Path]) -> Path:
    """Handle default destination for commands that operate on beancount files."""
    if destination is None:
        try:
            destination = find_default_beancount_file()
        except FileHandlerError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    return destination


def transaction_id_option() -> Any:
    """Create the --id option for targeting specific transactions."""
    return typer.Option(
        None, "--id", help="Target operation on a specific transaction ID only"
    )
