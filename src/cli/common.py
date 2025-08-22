"""Common CLI utilities and shared functionality."""

import os
import typer
from pathlib import Path
from typing import Optional, Any, Tuple

from .file_handler import find_default_beancount_file, FileHandlerError


def resolve_config_path(
    cli_value: Optional[Path], env_var_name: str, default_value: str, config_type: str
) -> Tuple[Path, str]:
    """Resolve configuration path with priority: CLI > env var > default.

    Returns:
        Tuple of (resolved_path, source_description)
    """
    if cli_value is not None:
        return cli_value, f"CLI argument (--{config_type.lower()})"

    env_value = os.getenv(env_var_name)
    if env_value:
        return Path(env_value), f"environment variable {env_var_name}"

    return Path(default_value), f"default ({default_value})"


def handle_default_ledger(ledger: Optional[Path]) -> Tuple[Path, str]:
    """Handle default ledger for commands that operate on beancount files.

    Returns:
        Tuple of (resolved_path, source_description)
    """
    resolved_path, source = resolve_config_path(
        ledger, "PEABODY_LEDGER", ".ledger/", "ledger"
    )

    # If using default or env var, try to find actual beancount file
    if ledger is None:
        try:
            actual_path = find_default_beancount_file()
            # Only use the found file if we're using the default value
            if source.startswith("default"):
                resolved_path = actual_path
                source = f"default (found {actual_path})"
        except FileHandlerError:
            # Keep the resolved path as is
            pass

    return resolved_path, source


def handle_default_destination(destination: Optional[Path]) -> Path:
    """Handle default destination for commands that operate on beancount files.

    DEPRECATED: Use handle_default_ledger instead.
    """
    ledger_path, _ = handle_default_ledger(destination)
    return ledger_path


def transaction_id_option() -> Any:
    """Create the --id option for targeting specific transactions."""
    return typer.Option(
        None, "--id", help="Target operation on a specific transaction ID only"
    )
