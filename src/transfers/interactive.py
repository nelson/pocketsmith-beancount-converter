"""Interactive mode for reviewing suspected transfers."""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

from .models import TransferPair, DetectionCriteria


class InteractiveReviewer:
    """Interactive UI for reviewing suspected transfer pairs."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize with optional console instance."""
        self.console = console or Console()

    def review_suspected_pairs(
        self,
        suspected_pairs: List[TransferPair],
        criteria: DetectionCriteria,
    ) -> tuple[List[TransferPair], List[TransferPair], DetectionCriteria]:
        """Review suspected pairs interactively.

        Returns:
            Tuple of (confirmed_pairs, rejected_pairs, updated_criteria)
        """
        if not suspected_pairs:
            self.console.print("[yellow]No suspected transfers to review.[/yellow]")
            return ([], [], criteria)

        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Found {len(suspected_pairs)} suspected transfer(s)[/bold cyan]\n"
                f"Review each pair and decide whether to confirm as transfer.",
                title="Interactive Transfer Review",
                border_style="cyan",
            )
        )
        self.console.print()

        confirmed: List[TransferPair] = []
        rejected: List[TransferPair] = []
        pattern_suggestions: Dict[str, Any] = {}

        for i, pair in enumerate(suspected_pairs, 1):
            self.console.print(
                f"[bold]Suspected Transfer {i}/{len(suspected_pairs)}[/bold]"
            )
            self.console.print()

            # Display pair details
            self._display_pair_details(pair)

            # Ask for decision
            self.console.print()
            decision = Prompt.ask(
                "[bold]Decision[/bold]",
                choices=["c", "r", "s", "q"],
                default="s",
            )

            if decision == "c":
                # Confirm as transfer
                confirmed.append(pair)
                self.console.print("[green]✓ Confirmed as transfer[/green]")

                # Track pattern for suggestions
                self._track_pattern(pair, pattern_suggestions)
            elif decision == "r":
                # Reject
                rejected.append(pair)
                self.console.print("[red]✗ Rejected[/red]")
            elif decision == "q":
                # Quit review
                self.console.print("[yellow]Review cancelled.[/yellow]")
                break
            else:
                # Skip for now
                self.console.print("[dim]⊘ Skipped[/dim]")

            self.console.print()
            self.console.print("─" * 60)
            self.console.print()

        # Show summary
        self._show_summary(confirmed, rejected, len(suspected_pairs))

        # Suggest criteria adjustments
        updated_criteria = self._suggest_criteria_adjustments(
            pattern_suggestions, criteria
        )

        return (confirmed, rejected, updated_criteria)

    def _display_pair_details(self, pair: TransferPair) -> None:
        """Display details of a transfer pair."""
        source_tx = pair.source_transaction
        dest_tx = pair.dest_transaction

        # Create table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("", style="dim", width=12)
        table.add_column("Source", style="cyan")
        table.add_column("Destination", style="green")

        # Add rows
        table.add_row("ID", str(source_tx.id), str(dest_tx.id))
        table.add_row("Date", str(source_tx.date), str(dest_tx.date))
        table.add_row(
            "Amount",
            f"{source_tx.amount} {source_tx.currency_code}",
            f"{dest_tx.amount} {dest_tx.currency_code}",
        )
        table.add_row("Payee", source_tx.payee or "", dest_tx.payee or "")

        if source_tx.account:
            source_account = source_tx.account.get("name", "")
        else:
            source_account = ""

        if dest_tx.account:
            dest_account = dest_tx.account.get("name", "")
        else:
            dest_account = ""

        table.add_row("Account", source_account, dest_account)

        self.console.print(table)
        self.console.print()

        # Show reason
        if pair.reason:
            reason_text = Text()
            reason_text.append("Reason: ", style="bold")
            reason_text.append(pair.reason, style="yellow")
            self.console.print(reason_text)
            self.console.print()

        # Show options
        self.console.print("[dim]Options:[/dim]")
        self.console.print("  [bold]c[/bold] = Confirm as transfer")
        self.console.print("  [bold]r[/bold] = Reject (not a transfer)")
        self.console.print("  [bold]s[/bold] = Skip (decide later)")
        self.console.print("  [bold]q[/bold] = Quit review")

    def _track_pattern(
        self, pair: TransferPair, pattern_suggestions: Dict[str, Any]
    ) -> None:
        """Track patterns from confirmed suspected transfers."""
        if not pair.reason:
            return

        # Track date delay patterns
        if "date-delay" in pair.reason:
            import re

            match = re.search(r"date-delay-(\d+)days", pair.reason)
            if match:
                days = int(match.group(1))
                pattern_suggestions.setdefault("date_delays", []).append(days)

        # Track FX patterns
        if "amount-mismatch-fx" in pair.reason:
            pattern_suggestions.setdefault("fx_count", 0)
            pattern_suggestions["fx_count"] += 1

    def _show_summary(
        self, confirmed: List[TransferPair], rejected: List[TransferPair], total: int
    ) -> None:
        """Show review summary."""
        self.console.print()
        self.console.print(
            Panel(
                f"[green]Confirmed: {len(confirmed)}[/green]\n"
                f"[red]Rejected: {len(rejected)}[/red]\n"
                f"[dim]Skipped: {total - len(confirmed) - len(rejected)}[/dim]",
                title="Review Summary",
                border_style="blue",
            )
        )

    def _suggest_criteria_adjustments(
        self, pattern_suggestions: Dict[str, Any], current_criteria: DetectionCriteria
    ) -> DetectionCriteria:
        """Suggest and apply criteria adjustments based on patterns."""
        if not pattern_suggestions:
            return current_criteria

        self.console.print()
        self.console.print("[bold cyan]Pattern Analysis[/bold cyan]")
        self.console.print()

        updated_criteria = DetectionCriteria(
            max_date_difference_days=current_criteria.max_date_difference_days,
            amount_tolerance=current_criteria.amount_tolerance,
            max_suspected_date_days=current_criteria.max_suspected_date_days,
            fx_amount_tolerance_percent=current_criteria.fx_amount_tolerance_percent,
            name_variations=current_criteria.name_variations,
            fx_enabled_accounts=current_criteria.fx_enabled_accounts,
        )

        # Suggest date delay adjustment
        if "date_delays" in pattern_suggestions:
            delays = pattern_suggestions["date_delays"]
            max_delay = max(delays)
            avg_delay = sum(delays) / len(delays)

            self.console.print(
                f"[yellow]⚠️[/yellow]  Detected {len(delays)} transfer(s) with date delays"
            )
            self.console.print(
                f"     Max delay: {max_delay} days, Average: {avg_delay:.1f} days"
            )
            self.console.print(
                f"     Current max_date_difference_days: {current_criteria.max_date_difference_days}"
            )

            if Confirm.ask(
                f"     Increase max_date_difference_days to {max_delay}?",
                default=True,
            ):
                updated_criteria.max_date_difference_days = max_delay
                self.console.print(f"     [green]✓ Updated to {max_delay} days[/green]")
            self.console.print()

        # Suggest FX tolerance
        if pattern_suggestions.get("fx_count", 0) > 0:
            fx_count = pattern_suggestions["fx_count"]
            self.console.print(
                f"[yellow]⚠️[/yellow]  Detected {fx_count} FX transfer(s) with amount mismatches"
            )
            self.console.print(
                "     These might be legitimate transfers with exchange rate differences"
            )
            self.console.print(
                "     Consider reviewing FX tolerance settings if needed"
            )
            self.console.print()

        return updated_criteria
