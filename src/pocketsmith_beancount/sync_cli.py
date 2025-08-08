"""CLI handler for synchronization operations."""

import sys
from typing import Any, Dict, List, Optional
from .sync_models import SyncResult
from .sync_enums import SyncStatus


class SyncCLIHandler:
    """Handler for sync command-line interface operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def confirm_sync_operation(
        self, local_count: int, remote_count: int, dry_run: bool = False
    ) -> bool:
        """
        Ask user to confirm sync operation.

        Args:
            local_count: Number of local transactions
            remote_count: Number of remote transactions
            dry_run: Whether this is a dry run

        Returns:
            True if user confirms, False otherwise
        """
        mode = "DRY RUN" if dry_run else "LIVE"
        print(f"\n{mode} Synchronization Summary:")
        print(f"  Local transactions: {local_count}")
        print(f"  Remote transactions: {remote_count}")
        print(f"  Total to process: {local_count + remote_count}")

        if dry_run:
            print("\nThis is a dry run - no actual changes will be made.")
        else:
            print("\nWARNING: This will make actual changes to your PocketSmith data!")

        while True:
            response = input("\nProceed with synchronization? (y/n): ").lower().strip()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def display_sync_progress(
        self, current: int, total: int, transaction_id: str
    ) -> None:
        """Display sync progress."""
        if self.verbose:
            percentage = (current / total) * 100 if total > 0 else 0
            print(
                f"[{current}/{total}] ({percentage:.1f}%) Processing transaction {transaction_id}"
            )

    def display_sync_results(
        self, results: List[SyncResult], dry_run: bool = False
    ) -> None:
        """
        Display synchronization results in a user-friendly format.

        Args:
            results: List of sync results
            dry_run: Whether this was a dry run
        """
        if not results:
            print("No transactions were processed.")
            return

        # Calculate summary statistics
        total = len(results)
        successful = sum(1 for r in results if r.status == SyncStatus.SUCCESS)
        errors = sum(1 for r in results if r.has_errors)
        warnings = sum(1 for r in results if r.has_warnings)
        changes = sum(len(r.changes) for r in results)
        conflicts = sum(len(r.conflicts) for r in results)

        # Display summary
        mode = "DRY RUN" if dry_run else "LIVE"
        print(f"\n{mode} Synchronization Results:")
        print("=" * 40)
        print(f"Total transactions processed: {total}")
        print(f"Successful: {successful}")
        print(f"Changes made: {changes}")
        print(f"Conflicts detected: {conflicts}")
        print(f"Warnings: {warnings}")
        print(f"Errors: {errors}")

        if total > 0:
            success_rate = (successful / total) * 100
            print(f"Success rate: {success_rate:.1f}%")

        # Display detailed results if verbose or if there are issues
        if self.verbose or errors > 0 or conflicts > 0:
            print("\nDetailed Results:")
            print("-" * 40)

            for result in results:
                if (
                    not self.verbose
                    and not result.has_errors
                    and not result.has_conflicts
                ):
                    continue

                print(f"\nTransaction {result.transaction_id}:")
                print(f"  Status: {result.status.name}")

                if result.changes:
                    print("  Changes:")
                    for change in result.changes:
                        print(
                            f"    {change.field_name}: '{change.old_value}' -> '{change.new_value}'"
                        )

                if result.conflicts:
                    print("  Conflicts:")
                    for conflict in result.conflicts:
                        print(
                            f"    {conflict.field_name}: local='{conflict.local_value}' vs remote='{conflict.remote_value}'"
                        )

                if result.errors:
                    print("  Errors:")
                    for error in result.errors:
                        print(f"    {error}")

                if result.warnings:
                    print("  Warnings:")
                    for warning in result.warnings:
                        print(f"    {warning}")

        # Display recommendations
        if errors > 0:
            print(
                f"\n⚠️  {errors} transactions had errors. Please review the detailed results above."
            )

        if conflicts > 0:
            print(
                f"\n⚠️  {conflicts} conflicts were detected. Review the resolution strategies if needed."
            )

        if dry_run and changes > 0:
            print(
                f"\n✅ Dry run completed. {changes} changes would be made in live mode."
            )
        elif not dry_run and changes > 0:
            print(
                f"\n✅ Synchronization completed. {changes} changes were made to PocketSmith."
            )
        elif changes == 0:
            print("\n✅ All transactions are already in sync. No changes needed.")

    def display_error(self, error_message: str, show_traceback: bool = False) -> None:
        """Display error message to user."""
        print(f"\n❌ Error: {error_message}", file=sys.stderr)

        if show_traceback:
            import traceback

            traceback.print_exc()

    def display_warning(self, warning_message: str) -> None:
        """Display warning message to user."""
        print(f"\n⚠️  Warning: {warning_message}")

    def display_info(self, info_message: str) -> None:
        """Display info message to user."""
        print(f"ℹ️  {info_message}")

    def format_field_changes(self, changes: List[Any]) -> str:
        """Format field changes for display."""
        if not changes:
            return "No changes"

        change_strs = []
        for change in changes[:3]:  # Show first 3 changes
            change_strs.append(
                f"{change.field_name}: {change.old_value} -> {change.new_value}"
            )

        if len(changes) > 3:
            change_strs.append(f"... and {len(changes) - 3} more")

        return ", ".join(change_strs)

    def get_user_choice(
        self, prompt: str, choices: List[str], default: Optional[str] = None
    ) -> str:
        """
        Get user choice from a list of options.

        Args:
            prompt: Prompt to display to user
            choices: List of valid choices
            default: Default choice if user presses enter

        Returns:
            User's choice
        """
        choices_str = "/".join(choices)
        if default:
            choices_str = choices_str.replace(default, default.upper())
            full_prompt = f"{prompt} ({choices_str}): "
        else:
            full_prompt = f"{prompt} ({choices_str}): "

        while True:
            response = input(full_prompt).strip().lower()

            if not response and default:
                return default

            if response in [choice.lower() for choice in choices]:
                return response

            print(f"Please enter one of: {', '.join(choices)}")

    def display_sync_configuration(self, config: Dict[str, Any]) -> None:
        """Display current sync configuration."""
        print("\nSynchronization Configuration:")
        print("-" * 30)

        for key, value in config.items():
            print(f"{key}: {value}")

        print()  # Empty line for spacing
