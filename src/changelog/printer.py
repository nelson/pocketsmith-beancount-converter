"""Terminal output formatting for changelog entries."""

import re
from typing import List, Optional, Dict, Any


class ColoredOutput:
    """ANSI color codes for terminal output."""

    # Colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GREY = "\033[90m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Reset
    RESET = "\033[0m"

    @classmethod
    def is_tty(cls) -> bool:
        """Check if output is to a TTY (supports colors)."""
        import sys

        return sys.stdout.isatty()

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Colorize text if TTY supports it."""
        if cls.is_tty():
            return f"{color}{text}{cls.RESET}"
        return text


class ChangelogPrinter:
    """Formats and prints changelog entries to terminal."""

    def __init__(self, use_colors: Optional[bool] = None):
        self.use_colors = (
            use_colors if use_colors is not None else ColoredOutput.is_tty()
        )

    def print_changelog_entries(self, entries: List[str]) -> None:
        """Print formatted changelog entries."""
        if not entries:
            print("No changelog entries to display.")
            return

        for entry in entries:
            formatted = self.format_change_entry(entry)
            print(formatted)

    def format_change_entry(self, entry: str) -> str:
        """Format a single changelog entry with colors and styling."""
        if not entry.strip():
            return ""

        # Parse the entry format: "timestamp OPERATION transaction_id [details]"
        parts = entry.split(
            " ", 4
        )  # Split into timestamp (3 parts), operation, transaction_id, details

        if len(parts) < 4:
            return entry  # Return as-is if format is unexpected

        timestamp_parts = parts[0:3]  # "Jan 15 14:32:45.123"
        operation = parts[3]
        remaining = " ".join(parts[4:]) if len(parts) > 4 else ""

        # Format timestamp
        timestamp_str = " ".join(timestamp_parts)
        if self.use_colors:
            timestamp_str = ColoredOutput.colorize(timestamp_str, ColoredOutput.GREY)

        # Format operation with color
        operation_colored = self._colorize_operation(operation)

        # Format the rest based on operation type
        if operation == "CREATE":
            transaction_id = remaining
            if self.use_colors:
                transaction_id = ColoredOutput.colorize(
                    transaction_id, ColoredOutput.GREEN
                )
            return f"{timestamp_str} {operation_colored} {transaction_id}"

        elif operation == "DELETE":
            transaction_id = remaining
            if self.use_colors:
                transaction_id = ColoredOutput.colorize(
                    transaction_id, ColoredOutput.RED
                )
            return f"{timestamp_str} {operation_colored} {transaction_id}"

        elif operation == "MODIFY":
            # Parse "transaction_id field1: old -> new, field2: old -> new"
            modify_parts = remaining.split(" ", 1)
            if len(modify_parts) >= 2:
                transaction_id, changes = modify_parts
                if self.use_colors:
                    transaction_id = ColoredOutput.colorize(
                        transaction_id, ColoredOutput.YELLOW
                    )
                    changes = self._colorize_field_changes(changes)
                return f"{timestamp_str} {operation_colored} {transaction_id} {changes}"
            else:
                return f"{timestamp_str} {operation_colored} {remaining}"

        else:
            return f"{timestamp_str} {operation_colored} {remaining}"

    def _colorize_operation(self, operation: str) -> str:
        """Colorize operation based on type."""
        if not self.use_colors:
            return operation

        if operation == "CREATE":
            return ColoredOutput.colorize(
                operation, ColoredOutput.GREEN + ColoredOutput.BOLD
            )
        elif operation == "DELETE":
            return ColoredOutput.colorize(
                operation, ColoredOutput.RED + ColoredOutput.BOLD
            )
        elif operation == "MODIFY":
            return ColoredOutput.colorize(
                operation, ColoredOutput.YELLOW + ColoredOutput.BOLD
            )
        else:
            return ColoredOutput.colorize(
                operation, ColoredOutput.BLUE + ColoredOutput.BOLD
            )

    def _colorize_field_changes(self, changes_str: str) -> str:
        """Colorize field changes in format 'field: old -> new'."""
        if not self.use_colors:
            return changes_str

        # Use regex to find and colorize field changes
        # Pattern matches: field_name: old_value -> new_value
        pattern = r"(\w+): ([^-]+) -> ([^,]+)"

        def colorize_match(match: re.Match[str]) -> str:
            field = match.group(1)
            old_value = match.group(2).strip()
            new_value = match.group(3).strip()

            field_colored = ColoredOutput.colorize(field, ColoredOutput.CYAN)
            arrow = ColoredOutput.colorize("->", ColoredOutput.GREY)
            old_colored = ColoredOutput.colorize(old_value, ColoredOutput.RED)
            new_colored = ColoredOutput.colorize(new_value, ColoredOutput.GREEN)

            return f"{field_colored}: {old_colored} {arrow} {new_colored}"

        return re.sub(pattern, colorize_match, changes_str)

    def print_summary(self, stats: Dict[str, Any]) -> None:
        """Print a colored summary of changelog stats."""
        if not stats:
            return

        print("\nChangelog Summary:")

        total = stats.get("total", 0)
        created = stats.get("CREATE", 0)
        modified = stats.get("MODIFY", 0)
        deleted = stats.get("DELETE", 0)

        if self.use_colors:
            total_str = ColoredOutput.colorize(str(total), ColoredOutput.BOLD)
            created_str = ColoredOutput.colorize(str(created), ColoredOutput.GREEN)
            modified_str = ColoredOutput.colorize(str(modified), ColoredOutput.YELLOW)
            deleted_str = ColoredOutput.colorize(str(deleted), ColoredOutput.RED)
        else:
            total_str = str(total)
            created_str = str(created)
            modified_str = str(modified)
            deleted_str = str(deleted)

        print(f"  Total entries: {total_str}")
        print(f"  Created: {created_str}")
        print(f"  Modified: {modified_str}")
        print(f"  Deleted: {deleted_str}")


def format_change_entry(entry: str, use_colors: Optional[bool] = None) -> str:
    """Convenience function to format a single changelog entry."""
    printer = ChangelogPrinter(use_colors)
    return printer.format_change_entry(entry)
