"""Rule management commands for the CLI."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from datetime import datetime, timedelta

import typer
import yaml
from dotenv import load_dotenv

from ..rules.loader import RuleLoader
from ..rules.transformer import RuleTransformer
from ..rules.matcher import RuleMatcher
from ..beancount.read import read_ledger
from beancount.core import data as bc_data
from .date_options import DateOptions
from .date_parser import (
    expand_date_range,
    get_this_month_range,
    get_last_month_range,
    get_this_year_range,
    get_last_year_range,
)
from .validators import validate_date_options, ValidationError
from .changelog import ChangelogManager, determine_changelog_path
from .common import handle_default_ledger


# ANSI color codes for terminal output
class Colors:
    APPLY = "\033[1;93m"  # Bold intense yellow
    TRANSACTION = "\033[92m"  # Intense green
    RULE = "\033[94m"  # Blue
    CATEGORY = "\033[95m"  # Purple
    LABELS = "\033[90m"  # Grey
    UNDERLINE_CYAN = "\033[4;96m"  # Underline cyan
    RESET = "\033[0m"  # Reset to default


def _generate_unified_diff(
    original_transaction: str,
    modified_transaction: str,
    ledger_file_path: Optional[str] = None,
) -> str:
    """Generate a unified diff showing the before and after of a transaction."""
    import difflib
    from datetime import datetime
    import os

    # Get timestamps
    if ledger_file_path and os.path.exists(ledger_file_path):
        old_mtime = datetime.fromtimestamp(os.path.getmtime(ledger_file_path))
        old_timestamp = old_mtime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " +1100"
    else:
        old_timestamp = "2024-06-25 09:06:55.852 +1100"  # Default fallback

    new_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " +1100"

    original_lines = original_transaction.splitlines(keepends=True)
    modified_lines = modified_transaction.splitlines(keepends=True)

    # Calculate line counts for the @@ header
    old_count = len(original_lines)
    new_count = len(modified_lines)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"old {old_timestamp}",
        tofile=f"new {new_timestamp}",
        lineterm="",
        n=3,  # Show 3 lines of context around changes
    )

    diff_lines = list(diff)

    # Fix the formatting of the header lines
    if len(diff_lines) >= 3:
        # Ensure newlines after the --- and +++ lines
        if len(diff_lines) >= 1 and diff_lines[0].startswith("---"):
            diff_lines[0] = diff_lines[0].rstrip() + "\n"
        if len(diff_lines) >= 2 and diff_lines[1].startswith("+++"):
            diff_lines[1] = diff_lines[1].rstrip() + "\n"
        # Fix the @@ line to show proper line counts
        diff_lines[2] = f"@@ -1,{old_count} +1,{new_count} @@\n"

    return "".join(diff_lines)


def _format_transaction_text(
    transaction: Dict[str, Any], modified_transaction: Optional[Dict[str, Any]] = None
) -> str:
    """Format a transaction as beancount text using actual beancount data."""
    # Use modified transaction data if provided, otherwise use original
    source_transaction = modified_transaction if modified_transaction else transaction

    date_str = transaction.get("date", "")
    payee = transaction.get("payee", "")
    narration = source_transaction.get("narration", "")

    # Get the transaction flag (usually '*' or '!')
    flag = transaction.get("flag", "*")

    # Build the transaction text with metadata
    lines = []

    # Add tags based on the source transaction
    tags_str = ""
    labels = source_transaction.get("labels", [])
    if isinstance(labels, list) and labels:
        # Sort labels alphabetically
        sorted_labels = sorted(str(label) for label in labels)
        tags_str = " #" + " #".join(sorted_labels)

    # Transaction header - no extra indentation
    lines.append(f'{date_str} {flag} "{payee}" "{narration}"{tags_str}')

    # Metadata - proper indentation (4 spaces) - skip last_modified and closing_balance as requested
    tx_id = transaction.get("id")
    if tx_id:
        lines.append(f"    id: {tx_id}")

    # Use actual postings from the source transaction (original or modified)
    postings = source_transaction.get("postings", [])
    if postings:
        for posting in postings:
            account = posting.get("account", "")
            amount = posting.get("amount", 0.0)
            units = posting.get("units", "USD")

            # Account comes from the source transaction (original or modified)
            # No additional transformation needed here since modified_transaction already has updated postings

            # Format the posting line
            if amount >= 0:
                lines.append(f"  {account}  {amount} {units}")
            else:
                lines.append(f"  {account}  {amount} {units}")
    else:
        # Fallback if no postings data available - this shouldn't happen with real beancount data
        lines.append("  [Missing posting data]")

    return "\n".join(lines)


def _format_rule_yaml(rule: Any) -> str:
    """Format a rule in YAML format for display."""
    lines = []
    lines.append("  if:")

    if rule.precondition:
        if rule.precondition.merchant:
            lines.append(f"  - merchant: {rule.precondition.merchant}")
        if rule.precondition.category:
            lines.append(f"  - category: {rule.precondition.category}")
        if rule.precondition.account:
            lines.append(f"  - account: {rule.precondition.account}")
        if rule.precondition.metadata:
            for key, value in rule.precondition.metadata.items():
                lines.append(f"  - {key}: {value}")

    lines.append("  then:")

    if rule.transform:
        if rule.transform.category:
            lines.append(f"  - category: {rule.transform.category}")
        if rule.transform.labels:
            labels_str = ", ".join(rule.transform.labels)
            lines.append(f"  - labels: [{labels_str}]")
        if rule.transform.memo:
            lines.append(f"  - memo: {rule.transform.memo}")
        if rule.transform.metadata:
            for key, value in rule.transform.metadata.items():
                lines.append(f"  - {key}: {value}")

    return "\n".join(lines)


def _print_rule_application_entry(
    transaction: Dict[str, Any],
    rule: Any,
    applications: List[Any],
    matcher: Any,
    eligible_rules: List[Any],
    experimental_continue: bool = False,
    all_transactions: Optional[List[Dict[str, Any]]] = None,
    ledger_file_path: Optional[str] = None,
    force_show_diff: bool = False,
) -> None:
    """Print a single rule application entry in the new format."""
    transaction_id = transaction.get("id", "UNKNOWN")

    # 1. Separator line (40 characters)
    print("=" * 40)

    # 2. Summary line with colors
    print(
        f"{Colors.TRANSACTION}TRANSACTION{Colors.RESET} {Colors.UNDERLINE_CYAN}{transaction_id}{Colors.RESET} matches {Colors.RULE}RULE{Colors.RESET} {Colors.UNDERLINE_CYAN}{rule.id}{Colors.RESET}"
    )
    print()

    # 3. Transaction display - either as diff (if changes) or plain text (if no changes)
    has_successful_applications = force_show_diff or (
        applications and any(app.status.value == "SUCCESS" for app in applications)
    )

    if has_successful_applications:
        # Create modified transaction for diff with deep copy of postings
        import copy

        modified_transaction = copy.deepcopy(transaction)

        # Apply all successful transformations
        for app in applications:
            if app.status.value == "SUCCESS":
                if app.field_name.lower() == "category":
                    modified_transaction["category"] = str(app.new_value)
                    # Also update postings to reflect category change
                    new_category = str(app.new_value)
                    if "postings" in modified_transaction:
                        updated_postings = []
                        for posting in modified_transaction["postings"]:
                            updated_posting = posting.copy()
                            account = posting.get("account", "")
                            # Update the expense/income posting with the new category
                            if account.startswith(("Expenses:", "Income:")):
                                if not new_category.startswith(
                                    ("Expenses:", "Income:")
                                ):
                                    updated_posting["account"] = (
                                        f"Expenses:{new_category}"
                                    )
                                else:
                                    updated_posting["account"] = new_category
                            updated_postings.append(updated_posting)
                        modified_transaction["postings"] = updated_postings
                elif app.field_name.lower() == "labels":
                    # Handle labels correctly - merge new labels with existing ones
                    existing_labels = transaction.get("labels", [])
                    if not isinstance(existing_labels, list):
                        existing_labels = []

                    new_labels = app.new_value
                    if isinstance(new_labels, list):
                        # Merge existing labels with new ones, avoiding duplicates
                        all_labels = existing_labels.copy()
                        for label in new_labels:
                            if str(label) not in all_labels:
                                all_labels.append(str(label))
                        # Sort labels alphabetically
                        modified_transaction["labels"] = sorted(all_labels)
                    else:
                        # Single new label
                        all_labels = existing_labels.copy()
                        if str(new_labels) not in all_labels:
                            all_labels.append(str(new_labels))
                        # Sort labels alphabetically
                        modified_transaction["labels"] = sorted(all_labels)
                elif app.field_name.lower() == "memo":
                    modified_transaction["narration"] = str(app.new_value)

        # Generate and display diff
        original_text = _format_transaction_text(transaction)
        modified_text = _format_transaction_text(transaction, modified_transaction)

        # Check if there are actual differences
        if original_text.strip() == modified_text.strip():
            # No actual differences in formatted text, show as single space indent
            transaction_text = _format_transaction_text(transaction)
            indented_lines = [" " + line for line in transaction_text.splitlines()]
            print("\n".join(indented_lines))
        else:
            # There are differences, show as diff
            diff = _generate_unified_diff(
                original_text, modified_text, ledger_file_path
            )
            if diff.strip():  # Only print if diff is not empty
                print(diff)
            else:
                # Fallback to showing transaction with indent if diff is empty
                transaction_text = _format_transaction_text(transaction)
                indented_lines = [" " + line for line in transaction_text.splitlines()]
                print("\n".join(indented_lines))
    else:
        # Transaction matches but no changes - display with single space indent to align with diff
        transaction_text = _format_transaction_text(transaction)
        # Add single space indent to each line to align with diff output
        indented_lines = [" " + line for line in transaction_text.splitlines()]
        print("\n".join(indented_lines))

    # Add newline between transaction and rule info for readability
    print()

    # 4. Rule printout with colors
    print(
        f"Matches {Colors.RULE}RULE{Colors.RESET} {Colors.UNDERLINE_CYAN}{rule.id}{Colors.RESET}:"
    )
    rule_yaml = _format_rule_yaml(rule)
    print(rule_yaml)

    # 5-6. Experimental continue features
    if experimental_continue:
        # 5. Other rules that match this transaction
        other_matching_rules = []
        for potential_rule in eligible_rules:
            if potential_rule.id == rule.id:
                continue  # Skip the already applied rule

            temp_result = matcher.find_matching_rule(transaction, [potential_rule])
            if temp_result:
                matched_rule, _ = temp_result
                other_matching_rules.append(matched_rule)

        # Only print if there are other matching rules
        if other_matching_rules:
            print()
            print("Other rules that match this transaction:")
            for matched_rule in other_matching_rules:
                merchant_pattern = ""
                if matched_rule.precondition and matched_rule.precondition.merchant:
                    merchant_pattern = matched_rule.precondition.merchant

                payee = transaction.get("payee", "")
                print(
                    f"  {Colors.UNDERLINE_CYAN}{matched_rule.id}{Colors.RESET} MERCHANT {payee} ~= {merchant_pattern}"
                )

        # 6. Other transactions that match this rule
        other_matching_transactions = []
        if all_transactions:
            for other_transaction in all_transactions:
                if other_transaction.get("id") == transaction.get("id"):
                    continue  # Skip the current transaction

                temp_result = matcher.find_matching_rule(other_transaction, [rule])
                if temp_result:
                    other_matching_transactions.append(other_transaction)

        # Only print if there are other matching transactions
        if other_matching_transactions:
            print()
            print("Other transactions that match this rule:")
            for other_transaction in other_matching_transactions:
                payee = other_transaction.get("payee", "")
                amount = other_transaction.get("amount", "0.00")
                date = other_transaction.get("date", "")
                tx_id = other_transaction.get("id", "")
                print(
                    f"  {Colors.UNDERLINE_CYAN}{tx_id}{Colors.RESET} {payee} {amount} USD {date}"
                )

    print()  # Final newline after each entry


def _format_yaml_content(yaml_content: str) -> str:
    """Format YAML content with inline labels and proper spacing between rules.

    Based on the reference implementation from export_to_sheets.py format_all_yaml_files().
    """

    def replace_labels_with_indent(match: re.Match[str]) -> str:
        indent = match.group(1)
        labels_content = match.group(2)
        # Extract individual label items
        label_items = re.findall(r"^\s+-\s+(.+)$", labels_content, re.MULTILINE)
        if label_items:
            # Format as inline list
            return f"{indent}labels: [{', '.join(label_items)}]\n"
        else:
            return f"{indent}labels: []\n"

    # Replace multi-line labels with inline format
    yaml_content = re.sub(
        r"(\s+)labels:\s*\n((?:\s+-\s+.+\n)+)", replace_labels_with_indent, yaml_content
    )

    # Also handle empty labels that might be formatted as "labels: []" already
    yaml_content = re.sub(r"(\s+)labels:\s*\[\s*\]", r"\1labels: []", yaml_content)

    # Add empty lines between rules for readability
    # Pattern matches the end of a rule (labels or metadata line) followed immediately by another rule (- id:)
    yaml_content = re.sub(
        r"(\n  - (?:labels|metadata): [^\n]*\n)(- id:)", r"\1\n\2", yaml_content
    )
    # Also handle when metadata is multi-line (last line of metadata block)
    yaml_content = re.sub(r"(\n      - [^\n]*\n)(- id:)", r"\1\n\2", yaml_content)

    return yaml_content


def rule_add_command(
    if_params: List[str],
    then_params: List[str],
    ledger: Optional[Path] = None,
    rules_path: Optional[Path] = None,
) -> None:
    """Add a new transaction processing rule."""
    try:
        # Parse preconditions
        preconditions = _parse_rule_params(if_params, "precondition")
        transforms = _parse_rule_params(then_params, "transform")

        # Determine rules path for loading
        if rules_path:
            if rules_path.is_dir():
                # For add command with directory, create rules.yaml in the directory
                rules_file = rules_path / "rules.yaml"
            else:
                rules_file = rules_path
        else:
            # Find rules file using the existing logic
            rules_file = _find_rules_file(ledger, rules_path)

        # Load existing rules to determine next ID
        rule_loader = RuleLoader()
        try:
            result = rule_loader.load_rules(str(rules_file))
            existing_rules = result.rules
        except Exception:
            existing_rules = []

        # Find next available rule ID
        max_id = 0
        if existing_rules:
            max_id = max(rule.id for rule in existing_rules)
        next_id = max_id + 1

        # Create new rule entry
        new_rule_data = {
            "id": next_id,
            "if": _convert_preconditions_to_yaml(preconditions),
            "then": _convert_transforms_to_yaml(transforms),
        }

        # Add to rules file
        if rules_file.exists():
            with open(rules_file, "r") as f:
                rules_data = yaml.safe_load(f) or []
        else:
            rules_data = []
            # Create parent directory if it doesn't exist
            rules_file.parent.mkdir(parents=True, exist_ok=True)

        rules_data.append(new_rule_data)

        # Write back to file with formatting
        with open(rules_file, "w") as f:
            yaml_content = yaml.dump(
                rules_data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            formatted_content = _format_yaml_content(yaml_content)
            f.write(formatted_content)

        typer.echo(f"Added rule {next_id} to {rules_file}")

    except Exception as e:
        typer.echo(f"Error adding rule: {e}", err=True)
        raise typer.Exit(1)


def rule_remove_command(rule_id: int, rules_path: Optional[Path] = None) -> None:
    """Completely remove a transaction processing rule from the YAML file."""
    try:
        # Determine rules path for loading
        if rules_path:
            if rules_path.is_dir():
                # For remove command with directory, we need to find which file contains the rule
                # This is more complex, so let's load all rules first to find the right file
                rule_loader = RuleLoader()
                result = rule_loader.load_rules(str(rules_path))
                if not result.is_successful:
                    typer.echo(
                        f"Rule loading failed with {len(result.errors)} errors:",
                        err=True,
                    )
                    for error in result.errors:
                        typer.echo(f"  • {error}", err=True)
                    raise typer.Exit(1)

                # Find which file contains this rule ID
                rules_file = None
                for yaml_file in rules_path.glob("*.yaml"):
                    try:
                        with open(yaml_file, "r") as f:
                            rules_data = yaml.safe_load(f) or []
                        for rule in rules_data:
                            if rule.get("id") == rule_id:
                                rules_file = yaml_file
                                break
                        if rules_file:
                            break
                    except Exception:
                        continue

                if not rules_file:
                    typer.echo(
                        f"Error: Rule {rule_id} not found in directory", err=True
                    )
                    raise typer.Exit(1)
            else:
                rules_file = rules_path
        else:
            # Find rules file using the existing logic
            rules_file = _find_rules_file(None, rules_path)

        if not rules_file.exists():
            typer.echo(f"Error: Rules file not found: {rules_file}", err=True)
            raise typer.Exit(1)

        # Load rules
        with open(rules_file, "r") as f:
            rules_data = yaml.safe_load(f) or []

        # Find and completely remove the rule
        rule_found = False
        original_count = len(rules_data)
        rules_data = [rule for rule in rules_data if rule.get("id") != rule_id]

        if len(rules_data) < original_count:
            rule_found = True

        if not rule_found:
            typer.echo(f"Error: Rule {rule_id} not found", err=True)
            raise typer.Exit(1)

        # Write back to file with formatting
        with open(rules_file, "w") as f:
            yaml_content = yaml.dump(
                rules_data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            formatted_content = _format_yaml_content(yaml_content)
            f.write(formatted_content)

        typer.echo(f"Removed rule {rule_id}")

    except Exception as e:
        typer.echo(f"Error removing rule: {e}", err=True)
        raise typer.Exit(1)


def rule_disable_command(rule_id: int, rules_path: Optional[Path] = None) -> None:
    """Disable a transaction processing rule by setting disabled: true."""
    try:
        # Determine rules path for loading
        if rules_path:
            if rules_path.is_dir():
                # For disable command with directory, we need to find which file contains the rule
                rule_loader = RuleLoader()
                result = rule_loader.load_rules(str(rules_path))
                if not result.is_successful:
                    typer.echo(
                        f"Rule loading failed with {len(result.errors)} errors:",
                        err=True,
                    )
                    for error in result.errors:
                        typer.echo(f"  • {error}", err=True)
                    raise typer.Exit(1)

                # Find which file contains this rule ID
                rules_file = None
                for yaml_file in rules_path.glob("*.yaml"):
                    try:
                        with open(yaml_file, "r") as f:
                            rules_data = yaml.safe_load(f) or []
                        for rule in rules_data:
                            if rule.get("id") == rule_id:
                                rules_file = yaml_file
                                break
                        if rules_file:
                            break
                    except Exception:
                        continue

                if not rules_file:
                    typer.echo(
                        f"Error: Rule {rule_id} not found in directory", err=True
                    )
                    raise typer.Exit(1)
            else:
                rules_file = rules_path
        else:
            # Find rules file using the existing logic
            rules_file = _find_rules_file(None, rules_path)

        if not rules_file.exists():
            typer.echo(f"Error: Rules file not found: {rules_file}", err=True)
            raise typer.Exit(1)

        # Load rules
        with open(rules_file, "r") as f:
            rules_data = yaml.safe_load(f) or []

        # Find and disable the rule
        rule_found = False
        for rule in rules_data:
            if rule.get("id") == rule_id:
                rule["disabled"] = True
                rule_found = True
                break

        if not rule_found:
            typer.echo(f"Error: Rule {rule_id} not found", err=True)
            raise typer.Exit(1)

        # Write back to file with formatting
        with open(rules_file, "w") as f:
            yaml_content = yaml.dump(
                rules_data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            formatted_content = _format_yaml_content(yaml_content)
            f.write(formatted_content)

        typer.echo(f"Disabled rule {rule_id}")

    except Exception as e:
        typer.echo(f"Error disabling rule: {e}", err=True)
        raise typer.Exit(1)


def rule_enable_command(rule_id: int, rules_path: Optional[Path] = None) -> None:
    """Enable a transaction processing rule by removing the disabled key."""
    try:
        # Determine rules path for loading
        if rules_path:
            if rules_path.is_dir():
                # For enable command with directory, we need to find which file contains the rule
                rule_loader = RuleLoader()
                result = rule_loader.load_rules(str(rules_path))
                if not result.is_successful:
                    typer.echo(
                        f"Rule loading failed with {len(result.errors)} errors:",
                        err=True,
                    )
                    for error in result.errors:
                        typer.echo(f"  • {error}", err=True)
                    raise typer.Exit(1)

                # Find which file contains this rule ID
                rules_file = None
                for yaml_file in rules_path.glob("*.yaml"):
                    try:
                        with open(yaml_file, "r") as f:
                            rules_data = yaml.safe_load(f) or []
                        for rule in rules_data:
                            if rule.get("id") == rule_id:
                                rules_file = yaml_file
                                break
                        if rules_file:
                            break
                    except Exception:
                        continue

                if not rules_file:
                    typer.echo(
                        f"Error: Rule {rule_id} not found in directory", err=True
                    )
                    raise typer.Exit(1)
            else:
                rules_file = rules_path
        else:
            # Find rules file using the existing logic
            rules_file = _find_rules_file(None, rules_path)

        if not rules_file.exists():
            typer.echo(f"Error: Rules file not found: {rules_file}", err=True)
            raise typer.Exit(1)

        # Load rules
        with open(rules_file, "r") as f:
            rules_data = yaml.safe_load(f) or []

        # Find and enable the rule by removing the disabled key
        rule_found = False
        for rule in rules_data:
            if rule.get("id") == rule_id:
                if "disabled" in rule:
                    del rule["disabled"]
                rule_found = True
                break

        if not rule_found:
            typer.echo(f"Error: Rule {rule_id} not found", err=True)
            raise typer.Exit(1)

        # Write back to file with formatting
        with open(rules_file, "w") as f:
            yaml_content = yaml.dump(
                rules_data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            formatted_content = _format_yaml_content(yaml_content)
            f.write(formatted_content)

        typer.echo(f"Enabled rule {rule_id}")

    except Exception as e:
        typer.echo(f"Error enabling rule: {e}", err=True)
        raise typer.Exit(1)


def rule_apply_command(
    ruleset: Optional[str],
    dry_run: bool = False,
    ledger: Optional[Path] = None,
    rules_path: Optional[Path] = None,
    date_options: Optional[DateOptions] = None,
    ledgerset: Optional[str] = None,
    verbose: bool = False,
    experimental_continue: bool = False,
    force: bool = False,
) -> None:
    """Apply rules to transactions.

    If ruleset is not provided, all rules will be eligible for evaluation.
    The --force flag allows disabled rules to be included in evaluation.
    """
    load_dotenv()

    try:
        # Validate date options
        if date_options:
            try:
                validate_date_options(
                    date_options.from_date,
                    date_options.to_date,
                    date_options.this_month,
                    date_options.last_month,
                    date_options.this_year,
                    date_options.last_year,
                )
            except ValidationError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1)
        # Determine rules path for loading
        if rules_path:
            # Use the rules path directly (can be file or directory)
            rules_load_path = rules_path
        else:
            # Find rules file using the existing logic
            rules_load_path = _find_rules_file(ledger, rules_path)

        # Load rules
        rule_loader = RuleLoader()
        result = rule_loader.load_rules(str(rules_load_path), include_disabled=force)

        if not result.is_successful:
            typer.echo(
                f"Rule loading failed with {len(result.errors)} errors:", err=True
            )
            for error in result.errors:
                typer.echo(f"  • {error}", err=True)
            raise typer.Exit(1)

        all_rules = result.rules

        # No need to filter disabled rules here since the loader now handles this based on include_disabled parameter

        # Determine eligible rules
        if ruleset is not None:
            # Parse the ruleset to get specific rule IDs
            try:
                target_rule_ids = _parse_ruleset(ruleset, Path(rules_load_path))
            except Exception as e:
                typer.echo(f"Error parsing ruleset '{ruleset}': {e}", err=True)
                raise typer.Exit(1)

            # Find the specific rules
            eligible_rules = [rule for rule in all_rules if rule.id in target_rule_ids]
            found_rule_ids = {rule.id for rule in eligible_rules}
            missing_rule_ids = set(target_rule_ids) - found_rule_ids

            # For exact ID matches and YAML files, require all rules to be found
            if missing_rule_ids and not ruleset.endswith("x"):
                typer.echo(
                    f"Error: Rules not found: {sorted(missing_rule_ids)}", err=True
                )
                raise typer.Exit(1)

            if not eligible_rules:
                typer.echo(f"Error: No rules found for ruleset '{ruleset}'", err=True)
                raise typer.Exit(1)
        else:
            # All rules are eligible
            eligible_rules = all_rules

        # Set up ledger path using consistent resolution pattern
        try:
            beancount_file, _ = handle_default_ledger(ledger)
        except Exception as e:
            typer.echo(f"Error setting up ledger: {e}", err=True)
            raise typer.Exit(1)

        # Read transactions from local beancount files
        try:
            transactions = _read_transactions_for_rules(
                beancount_file, date_options, ledgerset
            )
        except Exception as e:
            typer.echo(f"Error reading transactions from ledger: {e}", err=True)
            raise typer.Exit(1)

        if not transactions:
            typer.echo("No transactions to process")
            return

        if not eligible_rules:
            typer.echo("No rules to apply")
            return

        # Set up transformation infrastructure - use empty categories since we're working with local data
        categories: List[Dict[str, Any]] = []

        changelog: Optional[ChangelogManager] = None
        if not dry_run:
            single_file = beancount_file.is_file()
            changelog_path = determine_changelog_path(beancount_file, single_file)
            changelog = ChangelogManager(changelog_path)

        transformer = RuleTransformer(categories, changelog)
        matcher = RuleMatcher()
        matcher.prepare_rules(eligible_rules)

        # Apply rules to transactions with new output format
        total_applications = 0
        total_matches = 0

        for transaction in transactions:
            # Find first matching rule for this transaction
            match_result = matcher.find_matching_rule(transaction, eligible_rules)

            if match_result:
                rule, matches = match_result
                total_matches += 1

                # Apply the transformation to get the applications
                if dry_run:
                    # For dry run, apply to a copy to see what would change
                    transaction_copy = transaction.copy()
                    applications = transformer.apply_transform(
                        transaction_copy, rule.transform, rule.id, matches
                    )
                else:
                    # Apply the transformation
                    applications = transformer.apply_transform(
                        transaction, rule.transform, rule.id, matches
                    )

                # Check if there are successful modifications
                has_modifications = bool(
                    applications
                    and any(app.status.value == "SUCCESS" for app in applications)
                )

                # Logic for when to show transactions:
                # 1. If has modifications -> always show (either as diff or indented text)
                # 2. If no modifications but experimental_continue -> show indented text
                # 3. If no modifications and no experimental_continue -> skip
                if not has_modifications and not experimental_continue:
                    continue

                # Use the new output format
                _print_rule_application_entry(
                    transaction,
                    rule,
                    applications,
                    matcher,
                    eligible_rules,
                    experimental_continue,
                    transactions,
                    str(beancount_file),
                    force_show_diff=has_modifications,
                )

                # Handle logging and applications for non-dry-run
                if not dry_run and has_modifications:
                    for app in applications:
                        if app.status.value == "SUCCESS":
                            total_applications += 1

                            # Write APPLY entry if supported by the changelog manager
                            try:
                                if changelog and hasattr(
                                    changelog, "write_apply_entry"
                                ):
                                    changelog.write_apply_entry(
                                        app.transaction_id,
                                        app.rule_id,
                                        app.field_name,
                                        str(app.new_value),
                                    )
                            except Exception:
                                pass

                            # Optional detailed logging via transformer
                            try:
                                if transformer.changelog and hasattr(
                                    transformer.changelog, "log_entry"
                                ):
                                    transformer.log_applications([app])
                            except Exception:
                                pass

                # Count applications for dry run
                if dry_run and has_modifications:
                    for app in applications:
                        if app.status.value == "SUCCESS":
                            total_applications += 1

                # Print final APPLY log line (as in the example)
                if has_modifications:
                    for app in applications:
                        if app.status.value == "SUCCESS":
                            timestamp = datetime.now().strftime("%b %d %H:%M:%S.%f")[
                                :-3
                            ]
                            field_display = (
                                str(app.new_value)
                                if app.field_name != "labels"
                                else str(app.new_value)
                            )
                            print(
                                f"[{timestamp}] {Colors.APPLY}APPLY{Colors.RESET} {Colors.UNDERLINE_CYAN}{app.transaction_id}{Colors.RESET} {Colors.RULE}RULE{Colors.RESET} {Colors.UNDERLINE_CYAN}{app.rule_id}{Colors.RESET} {app.field_name.upper()} {field_display}"
                            )
                            print()  # Add blank line after each application

        # Print summary
        rules_desc = f"ruleset {ruleset}" if ruleset else f"{len(eligible_rules)} rules"
        transactions_desc = f"{len(transactions)} transactions"

        if dry_run:
            typer.echo("\nDry run completed:")
        else:
            typer.echo("\nRule application completed:")

        typer.echo(f"  Processed {rules_desc} against {transactions_desc}")
        typer.echo(f"  Found {total_matches} matching transactions")
        typer.echo(f"  Applied {total_applications} field transformations")

    except Exception as e:
        typer.echo(f"Error applying rules: {e}", err=True)
        raise typer.Exit(1)


def _parse_rule_params(params: List[str], param_type: str) -> Dict[str, Any]:
    """Parse rule parameters from --if or --then options."""
    result: Dict[str, Any] = {}

    for param in params:
        if "=" not in param:
            typer.echo(
                f"Error: Invalid {param_type} format '{param}'. Expected key=value",
                err=True,
            )
            raise typer.Exit(1)

        key, value = param.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or not value:
            typer.echo(
                f"Error: Invalid {param_type} format '{param}'. Key and value cannot be empty",
                err=True,
            )
            raise typer.Exit(1)

        # Handle metadata specially for preconditions
        if param_type == "precondition" and key not in [
            "account",
            "category",
            "merchant",
        ]:
            # Treat as metadata
            if "metadata" not in result:
                result["metadata"] = {}
            if isinstance(result["metadata"], dict):
                result["metadata"][key] = value
        else:
            result[key] = value

    return result


def _convert_preconditions_to_yaml(
    preconditions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert parsed preconditions to YAML format."""
    yaml_conditions = []

    for key, value in preconditions.items():
        if key == "metadata":
            yaml_conditions.append({key: value})
        else:
            yaml_conditions.append({key: value})

    return yaml_conditions


def _convert_transforms_to_yaml(transforms: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert parsed transforms to YAML format."""
    yaml_transforms: List[Dict[str, Any]] = []

    for key, value in transforms.items():
        # Handle special metadata keys
        if key not in ["category", "labels", "tags", "memo", "narration", "metadata"]:
            # Treat as metadata
            if not any("metadata" in t for t in yaml_transforms):
                yaml_transforms.append({"metadata": {}})

            # Find the metadata transform and add to it
            for transform in yaml_transforms:
                if "metadata" in transform:
                    transform["metadata"][key] = value
                    break
        else:
            yaml_transforms.append({key: value})

    return yaml_transforms


def rule_list_command(
    verbose: bool = False,
    rule_id: Optional[str] = None,
    rules_path: Optional[Path] = None,
) -> None:
    """List all rules found."""
    try:
        # Determine rules path for loading using consistent resolution pattern
        if rules_path:
            rules_load_path = rules_path
        else:
            # Use consistent ledger resolution pattern for rules
            ledger_path, _ = handle_default_ledger(None)
            rules_load_path = _find_rules_file(ledger_path, rules_path)

        # Load rules
        rule_loader = RuleLoader()
        result = rule_loader.load_rules(str(rules_load_path))

        if not result.is_successful:
            typer.echo(
                f"Rule loading failed with {len(result.errors)} errors:", err=True
            )
            for error in result.errors:
                typer.echo(f"  • {error}", err=True)
            raise typer.Exit(1)

        all_rules = result.rules

        # Parse rule ID filter if provided
        if rule_id:
            filtered_rule_ids = _parse_rule_ids(rule_id)
            all_rules = [rule for rule in all_rules if rule.id in filtered_rule_ids]

        if not all_rules:
            if rule_id:
                typer.echo(f"No rules found matching ID filter: {rule_id}")
            else:
                typer.echo("No rules found")
            return

        if verbose:
            # Show detailed rule information
            typer.echo("RULES:")
            typer.echo()
            for rule in all_rules:
                disabled_status = (
                    " (DISABLED)" if getattr(rule, "disabled", False) else ""
                )
                typer.echo(f"RULE {rule.id}{disabled_status}")

                # Show conditions
                if rule.precondition:
                    typer.echo("  IF:")
                    # RulePrecondition has direct fields
                    if rule.precondition.account:
                        typer.echo(f"    ACCOUNT: {rule.precondition.account}")
                    if rule.precondition.category:
                        typer.echo(f"    CATEGORY: {rule.precondition.category}")
                    if rule.precondition.merchant:
                        typer.echo(f"    MERCHANT: {rule.precondition.merchant}")
                    if rule.precondition.metadata:
                        typer.echo(f"    METADATA: {rule.precondition.metadata}")

                # Show transforms
                if rule.transform:
                    typer.echo("  THEN:")
                    # RuleTransform has direct fields, not a transforms list
                    if rule.transform.category:
                        typer.echo(f"    CATEGORY: {rule.transform.category}")
                    if rule.transform.labels:
                        typer.echo(f"    LABELS: {rule.transform.labels}")
                    if rule.transform.memo:
                        typer.echo(f"    MEMO: {rule.transform.memo}")
                    if rule.transform.metadata:
                        typer.echo(f"    METADATA: {rule.transform.metadata}")

                typer.echo()
        else:
            # Show summary
            typer.echo(f"Found {len(all_rules)} rules")

            # Group by file if loading from directory
            if rules_load_path and Path(rules_load_path).is_dir():
                files_info = _group_rules_by_file(rules_load_path, all_rules)

                typer.echo(f"Loaded from {len(files_info)} files:")
                for file_name, rules in files_info.items():
                    rule_ids = [rule.id for rule in rules]
                    rule_id_ranges = _consolidate_id_ranges(rule_ids)
                    typer.echo(
                        f"  {file_name}: {len(rules)} rules (IDs: {rule_id_ranges})"
                    )

            # Group by destination category
            category_counts: Dict[str, int] = {}
            for rule in all_rules:
                # Extract category from transform
                category = "unknown"
                if rule.transform and rule.transform.category:
                    category = rule.transform.category

                category_counts[category] = category_counts.get(category, 0) + 1

            if category_counts:
                typer.echo("\nRules by destination category:")
                for category, count in sorted(category_counts.items()):
                    typer.echo(f"  {category}: {count} rules")

    except Exception as e:
        typer.echo(f"Error listing rules: {e}", err=True)
        raise typer.Exit(1)


def rule_lookup_command(
    merchant: Optional[str] = None,
    category: Optional[str] = None,
    account: Optional[str] = None,
    rules_path: Optional[Path] = None,
) -> None:
    """Look up which rule would match given transaction data."""
    try:
        # Validate at least one parameter is provided
        if not any([merchant, category, account]):
            typer.echo(
                "Error: At least one of --merchant, --category, or --account must be provided",
                err=True,
            )
            raise typer.Exit(1)

        # Determine rules path for loading using consistent resolution pattern
        if rules_path:
            rules_load_path = rules_path
        else:
            # Use consistent ledger resolution pattern for rules
            ledger_path, _ = handle_default_ledger(None)
            rules_load_path = _find_rules_file(ledger_path, rules_path)

        # Load rules
        rule_loader = RuleLoader()
        result = rule_loader.load_rules(str(rules_load_path))

        if not result.is_successful:
            typer.echo(
                f"Rule loading failed with {len(result.errors)} errors:", err=True
            )
            for error in result.errors:
                typer.echo(f"  • {error}", err=True)
            raise typer.Exit(1)

        all_rules = result.rules

        # Filter out disabled rules - they should be ignored for lookup
        all_rules = [rule for rule in all_rules if not getattr(rule, "disabled", False)]

        if not all_rules:
            typer.echo("No rules found")
            return

        # Create a mock transaction for matching
        mock_transaction = {}
        if merchant:
            mock_transaction["payee"] = merchant
        if category:
            mock_transaction["category"] = category
        if account:
            mock_transaction["account"] = account

        # Use the rule matcher to find matching rule
        matcher = RuleMatcher()
        matcher.prepare_rules(all_rules)

        match_result = matcher.find_matching_rule(mock_transaction, all_rules)

        if match_result:
            rule, matches = match_result

            # Generate a mock transaction ID for display
            transaction_id = "LOOKUP_001"

            typer.echo(f"TRANSACTION {transaction_id} matches RULE {rule.id}")
            typer.echo()

            # Show matched conditions
            for field_name, match_obj in matches.items():
                # Get the pattern from the rule's precondition
                if field_name == "merchant":
                    pattern = rule.precondition.merchant
                    value = merchant
                elif field_name == "category":
                    pattern = rule.precondition.category
                    value = category
                elif field_name == "account":
                    pattern = rule.precondition.account
                    value = account
                else:
                    pattern = "unknown"
                    value = "unknown"

                typer.echo(f"  {field_name.upper()} {value} ~= {pattern}")

            typer.echo()

            # Show transforms that would be applied
            if rule.transform:
                if rule.transform.category:
                    old_value = category or "N/A"
                    typer.echo(f"  CATEGORY {old_value} -> {rule.transform.category}")
                if rule.transform.labels:
                    typer.echo(f"  LABELS N/A -> {rule.transform.labels}")
                if rule.transform.memo:
                    typer.echo(f"  MEMO N/A -> {rule.transform.memo}")
                if rule.transform.metadata:
                    typer.echo("  METADATA")
                    for key, val in rule.transform.metadata.items():
                        typer.echo(f"    NEW {key}: {val}")
        else:
            typer.echo("No matching rule found for the given transaction data")

    except Exception as e:
        typer.echo(f"Error looking up rules: {e}", err=True)
        raise typer.Exit(1)


def _group_rules_by_file(
    directory_path: Path, all_rules: List[Any]
) -> Dict[str, List[Any]]:
    """Group rules by their source file by re-loading individual files."""
    from ..rules.loader import RuleLoader

    files_info = {}
    yaml_files = list(directory_path.glob("*.yaml")) + list(
        directory_path.glob("*.yml")
    )

    # Create a mapping from rule ID to rule object for fast lookup
    rule_map = {rule.id: rule for rule in all_rules}

    for yaml_file in sorted(yaml_files):
        # Load each file individually to get its rules
        loader = RuleLoader()
        result = loader.load_rules(yaml_file)

        if result.is_successful:
            file_name = yaml_file.name
            file_rules = []

            # Find the corresponding rule objects from the main list
            for loaded_rule in result.rules:
                if loaded_rule.id in rule_map:
                    file_rules.append(rule_map[loaded_rule.id])

            if file_rules:
                files_info[file_name] = file_rules

    return files_info


def _consolidate_id_ranges(rule_ids: List[int]) -> str:
    """Consolidate a list of rule IDs into range notation.

    Example: [1,3,4,5,7,8,10] -> "1, 3-5, 7-8, 10"
    """
    if not rule_ids:
        return ""

    sorted_ids = sorted(set(rule_ids))
    ranges = []
    start = sorted_ids[0]
    end = sorted_ids[0]

    for i in range(1, len(sorted_ids)):
        if sorted_ids[i] == end + 1:
            # Consecutive number, extend range
            end = sorted_ids[i]
        else:
            # Gap found, finalize current range
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = sorted_ids[i]

    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def _parse_rule_ids(rule_id_string: str) -> List[int]:
    """Parse rule ID string into list of integers.

    Supports formats like: 1,3-5,7-8 -> [1,3,4,5,7,8]
    """
    result: List[int] = []

    for part in rule_id_string.split(","):
        part = part.strip()
        if "-" in part:
            # Handle range like "3-5"
            start, end = part.split("-", 1)
            try:
                start_id = int(start.strip())
                end_id = int(end.strip())
                result.extend(range(start_id, end_id + 1))
            except ValueError:
                typer.echo(f"Error: Invalid rule ID range '{part}'", err=True)
                raise typer.Exit(1)
        else:
            # Handle single ID
            try:
                result.append(int(part))
            except ValueError:
                typer.echo(f"Error: Invalid rule ID '{part}'", err=True)
                raise typer.Exit(1)

    return sorted(list(set(result)))  # Remove duplicates and sort


def _parse_ruleset(ruleset_string: Union[str, int], rules_path: Path) -> List[int]:
    """Parse ruleset string into list of rule IDs.

    Supports multiple formats:
    1. Numeric IDs: 1,3-5,9-11 -> [1,3,4,5,9,10,11]
    2. Wildcards: 1x -> [10-19], 3x -> [3000-3999], 25x -> [250-259]
    3. YAML files: rules.yaml -> all rule IDs from that file
    """

    # Convert integer to string for backward compatibility
    if isinstance(ruleset_string, int):
        ruleset_string = str(ruleset_string)

    # Check if it's a YAML file
    if ruleset_string.endswith(".yaml"):
        return _get_rule_ids_from_yaml_file(ruleset_string, rules_path)

    # Check if it contains wildcard pattern (digit followed by x)
    if "x" in ruleset_string:
        return _parse_wildcard_rulesets(ruleset_string)

    # Otherwise, use the existing numeric ID parsing
    return _parse_rule_ids(ruleset_string)


def _parse_wildcard_rulesets(ruleset_string: str) -> List[int]:
    """Parse wildcard ruleset patterns.

    Each 'x' represents exactly one digit (0-9).

    Examples:
    - 1x -> [10-19] (1 followed by 1 digit)
    - 3x -> [30-39] (3 followed by 1 digit)
    - 3xxx -> [3000-3999] (3 followed by 3 digits)
    - 25x -> [250-259] (25 followed by 1 digit)
    - 1xx -> [100-199] (1 followed by 2 digits)
    - 1x,3xxx -> [10-19, 3000-3999] (combinations)
    """
    result: List[int] = []

    for part in ruleset_string.split(","):
        part = part.strip()

        # Check for wildcard pattern: digits followed by one or more 'x'
        wildcard_match = re.match(r"^(\d+)(x+)$", part)
        if wildcard_match:
            prefix = wildcard_match.group(1)
            x_count = len(wildcard_match.group(2))  # Count of 'x' characters

            # Calculate range based on number of x's:
            # 1x -> 10-19 (1 followed by 1 digit)
            # 3x -> 30-39 (3 followed by 1 digit)
            # 3xxx -> 3000-3999 (3 followed by 3 digits)
            # 25x -> 250-259 (25 followed by 1 digit)
            # Each 'x' represents exactly one digit (0-9)

            range_size = 10**x_count
            start = int(prefix) * range_size
            end = start + range_size - 1

            result.extend(range(start, end + 1))
        else:
            # Fall back to regular ID parsing for non-wildcard parts
            if "-" in part:
                start, end_part = part.split("-", 1)
                try:
                    start_id = int(start.strip())
                    end_id = int(end_part.strip())
                    result.extend(range(start_id, end_id + 1))
                except ValueError:
                    typer.echo(f"Error: Invalid rule ID range '{part}'", err=True)
                    raise typer.Exit(1)
            else:
                try:
                    result.append(int(part))
                except ValueError:
                    typer.echo(f"Error: Invalid rule ID '{part}'", err=True)
                    raise typer.Exit(1)

    return sorted(list(set(result)))


def _get_rule_ids_from_yaml_file(yaml_filename: str, rules_path: Path) -> List[int]:
    """Get all rule IDs from a specific YAML file."""
    yaml_file_path = rules_path / yaml_filename

    if not yaml_file_path.exists():
        typer.echo(
            f"Error: Rule file '{yaml_filename}' not found in {rules_path}", err=True
        )
        raise typer.Exit(1)

    # Load the specific YAML file to get its rule IDs
    rule_loader = RuleLoader()
    try:
        result = rule_loader.load_rules(str(yaml_file_path))
        if result.errors:
            typer.echo(
                f"Rule loading failed with {len(result.errors)} errors:", err=True
            )
            for error in result.errors:
                typer.echo(f"  • {error}", err=True)
            raise typer.Exit(1)

        rule_ids = [rule.id for rule in result.rules]
        if not rule_ids:
            typer.echo(f"Warning: No rules found in file '{yaml_filename}'")

        return sorted(rule_ids)

    except Exception as e:
        typer.echo(f"Error loading rules from '{yaml_filename}': {e}", err=True)
        raise typer.Exit(1)


def _read_transactions_for_rules(
    beancount_path: Path, date_options: Optional[DateOptions], ledgerset: Optional[str]
) -> List[Dict[str, Any]]:
    """Read transactions from beancount files for rule processing.

    Always reads the complete ledger for proper validation, then filters based on
    ledgerset or date options.

    Returns list of transaction dictionaries compatible with rule matcher.
    """
    single_file = beancount_path.is_file()

    # Always read the complete ledger to avoid validation errors
    all_transactions = _read_all_transactions(beancount_path, single_file)

    if ledgerset:
        # Try to get transaction IDs from specific ledgerset files
        target_transaction_ids = _get_transaction_ids_from_ledgerset(
            beancount_path, ledgerset
        )

        if target_transaction_ids:
            # Filter complete ledger transactions to only those in the ledgerset
            transactions = [
                tx for tx in all_transactions if tx.get("id") in target_transaction_ids
            ]
            typer.echo(
                f"Ledgerset '{ledgerset}' filtered to {len(transactions)} transactions"
            )
        else:
            # Fall back to date-based filtering if no files found but pattern matches date ranges
            date_ranges = _extract_date_ranges_from_ledgerset(ledgerset)
            if date_ranges:
                transactions = []
                for transaction in all_transactions:
                    transaction_date = _get_transaction_date(transaction)
                    if transaction_date and _transaction_matches_date_ranges(
                        transaction_date, date_ranges
                    ):
                        transactions.append(transaction)
                typer.echo(
                    f"Ledgerset '{ledgerset}' date-filtered to {len(transactions)} transactions"
                )
            else:
                typer.echo(
                    f"Warning: No transactions found for ledgerset '{ledgerset}'"
                )
                transactions = []
    else:
        transactions = all_transactions

        if date_options:
            # Apply date filtering
            original_count = len(transactions)
            transactions = _filter_transactions_by_date_options(
                transactions, date_options
            )
            filtered_count = len(transactions)
            typer.echo(
                f"Date options filtered {original_count} transactions to {filtered_count}"
            )
        else:
            typer.echo(f"Read {len(transactions)} transactions from ledger")

    return transactions


def _get_transaction_ids_from_ledgerset(
    beancount_path: Path, ledgerset: str
) -> Set[str]:
    """Get transaction IDs from specific ledgerset files."""
    transaction_ids = set()

    # Resolve ledgerset path
    if ledgerset.startswith("/"):
        ledgerset_path = Path(ledgerset)
    else:
        ledgerset_path = beancount_path / ledgerset

    # Check if it's a directory or file
    if ledgerset_path.is_dir():
        # Read all .beancount files in directory
        for file_path in ledgerset_path.glob("*.beancount"):
            transaction_ids.update(_get_transaction_ids_from_file(file_path))
    elif ledgerset_path.is_file() or (
        ledgerset_path.with_suffix(".beancount").is_file()
    ):
        # Read specific file (with or without .beancount extension)
        if ledgerset_path.is_file():
            transaction_ids.update(_get_transaction_ids_from_file(ledgerset_path))
        else:
            transaction_ids.update(
                _get_transaction_ids_from_file(ledgerset_path.with_suffix(".beancount"))
            )
    else:
        # Try to interpret as year/month pattern - use date filtering approach
        date_ranges = _extract_date_ranges_from_ledgerset(ledgerset)
        if date_ranges:
            # This will be handled by date filtering on the complete ledger
            typer.echo(
                f"Warning: Pattern-based ledgerset '{ledgerset}' will use date filtering instead"
            )
        else:
            typer.echo(f"Warning: Could not find ledgerset '{ledgerset}'")

    return transaction_ids


def _get_transaction_ids_from_file(file_path: Path) -> Set[str]:
    """Extract transaction IDs from a beancount file without full validation."""
    transaction_ids = set()

    try:
        # Use a simpler approach - read the file directly and extract IDs
        with open(file_path, "r", encoding="utf-8") as f:
            current_id = None
            for line in f:
                line = line.strip()
                # Look for ID in metadata
                if line.startswith("id:"):
                    try:
                        current_id = line.split(":", 1)[1].strip().strip("\"'")
                        if current_id:
                            transaction_ids.add(current_id)
                    except (IndexError, ValueError):
                        pass
    except Exception as e:
        typer.echo(
            f"Warning: Could not read transaction IDs from {file_path}: {e}", err=True
        )

    return transaction_ids


def _read_all_transactions(
    beancount_path: Path, single_file: bool
) -> List[Dict[str, Any]]:
    """Read all transactions from the beancount ledger."""
    transactions = []

    if single_file:
        # Read from single file
        transactions = _read_transactions_from_file(beancount_path)
    else:
        # Read from main.beancount which includes all other files
        main_file = beancount_path / "main.beancount"
        if main_file.exists():
            transactions = _read_transactions_from_file(main_file)
        else:
            # Fallback: read all .beancount files in directory
            for file_path in beancount_path.glob("**/*.beancount"):
                transactions.extend(_read_transactions_from_file(file_path))

    return transactions


def _read_transactions_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read transactions from a single beancount file and convert to rule-compatible format."""
    try:
        # Suppress both logger output and stderr for validation errors
        import logging
        import os
        from contextlib import redirect_stderr

        beancount_logger = logging.getLogger("src.beancount.read")
        old_level = beancount_logger.level
        beancount_logger.setLevel(logging.ERROR)

        try:
            # Also suppress stderr to catch beancount loader validation errors
            with open(os.devnull, "w") as devnull:
                with redirect_stderr(devnull):
                    entries, _errors, _opts = read_ledger(str(file_path))
        finally:
            beancount_logger.setLevel(old_level)

    except Exception as e:
        typer.echo(f"Warning: Failed to read {file_path}: {e}", err=True)
        return []

    transactions = []
    for entry in entries:
        if isinstance(entry, bc_data.Transaction):
            transaction = _convert_beancount_transaction_to_dict(entry)
            if transaction:
                transactions.append(transaction)

    return transactions


def _convert_beancount_transaction_to_dict(
    entry: bc_data.Transaction,
) -> Optional[Dict[str, Any]]:
    """Convert a beancount Transaction to a dictionary compatible with rule matcher."""
    meta = entry.meta or {}
    tx_id = meta.get("id")
    if tx_id is None:
        return None

    # Extract category from postings
    category = None
    for posting in entry.postings:
        account = posting.account
        if account.startswith(("Expenses:", "Income:")):
            # Use account name as category for rule matching
            category = account
            break

    # Convert postings to dictionary format
    postings_data = []
    for posting in entry.postings:
        posting_dict = {
            "account": posting.account,
            "amount": float(posting.units.number)
            if posting.units and posting.units.number is not None
            else 0.0,
            "units": posting.units.currency if posting.units else "USD",
        }
        postings_data.append(posting_dict)

    # Build transaction dictionary with full beancount data preserved
    transaction = {
        "id": str(tx_id),
        "date": entry.date.strftime("%Y-%m-%d"),
        "payee": entry.payee or "",
        "category": category,
        "labels": list(entry.tags) if entry.tags else [],
        "narration": entry.narration or "",
        "flag": entry.flag or "*",
        "postings": postings_data,
        # Optional metadata
        "last_modified": meta.get("last_modified"),
        "closing_balance": meta.get("closing_balance"),
    }

    return transaction


def _filter_transactions_by_date_options(
    transactions: List[Dict[str, Any]], date_options: DateOptions
) -> List[Dict[str, Any]]:
    """Filter transactions based on date options."""
    # Convert date options to date range
    start_str: Optional[str]
    end_str: Optional[str]

    if date_options.this_month:
        start, end = get_this_month_range()
        start_str, end_str = start.isoformat(), end.isoformat()
    elif date_options.last_month:
        start, end = get_last_month_range()
        start_str, end_str = start.isoformat(), end.isoformat()
    elif date_options.this_year:
        start, end = get_this_year_range()
        start_str, end_str = start.isoformat(), end.isoformat()
    elif date_options.last_year:
        start, end = get_last_year_range()
        start_str, end_str = start.isoformat(), end.isoformat()
    elif date_options.from_date or date_options.to_date:
        start, end = expand_date_range(date_options.from_date, date_options.to_date)
        start_str = start.isoformat() if start else None
        end_str = end.isoformat() if end else None
    else:
        # No date filtering
        return transactions

    # Filter transactions
    filtered_transactions = []
    for transaction in transactions:
        tx_date = transaction.get("date")
        if tx_date:
            if start_str and tx_date < start_str:
                continue
            if end_str and tx_date > end_str:
                continue
            filtered_transactions.append(transaction)

    return filtered_transactions


def _choose_date_range(
    changelog: ChangelogManager,
    date_options: Optional[DateOptions],
) -> Tuple[Optional[str], Optional[str]]:
    """Determine date range from options or last sync info."""
    if not date_options:
        # No date options provided, use last sync info or reasonable defaults
        last = changelog.get_last_sync_info()
        if last:
            _, from_date, to_date = last
            return from_date, to_date
        else:
            # No sync info, get recent transactions (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            return start_date.isoformat()[:10], end_date.isoformat()[:10]

    if date_options.this_month:
        start, end = get_this_month_range()
        return start.isoformat(), end.isoformat()
    if date_options.last_month:
        start, end = get_last_month_range()
        return start.isoformat(), end.isoformat()
    if date_options.this_year:
        start, end = get_this_year_range()
        return start.isoformat(), end.isoformat()
    if date_options.last_year:
        start, end = get_last_year_range()
        return start.isoformat(), end.isoformat()
    if date_options.from_date or date_options.to_date:
        start, end = expand_date_range(date_options.from_date, date_options.to_date)
        return start.isoformat() if start else None, end.isoformat() if end else None

    # No specific date options, use last sync info or reasonable defaults
    last = changelog.get_last_sync_info()
    if last:
        _, from_date, to_date = last
        return from_date, to_date
    else:
        # No sync info, get recent transactions (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        return start_date.isoformat()[:10], end_date.isoformat()[:10]


def _filter_transactions_by_ledgerset(
    transactions: List[Dict[str, Any]], ledgerset: str, ledger_base_path: Path
) -> List[Dict[str, Any]]:
    """Filter transactions to only those that would be written to the specified ledgerset file/directory.

    Args:
        transactions: List of transaction dictionaries
        ledgerset: File or directory path relative to ledger (e.g., "2025/2025-08.beancount", "2025/")
        ledger_base_path: Base ledger path

    Returns:
        Filtered list of transactions
    """

    # Extract date range from the ledgerset path
    date_ranges = _extract_date_ranges_from_ledgerset(ledgerset)

    if not date_ranges:
        # If we can't determine date ranges, return all transactions
        typer.echo(
            f"Warning: Could not determine date range from ledgerset '{ledgerset}'"
        )
        return transactions

    # Filter transactions based on their dates
    filtered_transactions = []
    for transaction in transactions:
        transaction_date = _get_transaction_date(transaction)
        if transaction_date and _transaction_matches_date_ranges(
            transaction_date, date_ranges
        ):
            filtered_transactions.append(transaction)

    return filtered_transactions


def _extract_date_ranges_from_ledgerset(
    ledgerset: str,
) -> List[Tuple[datetime, datetime]]:
    """Extract date ranges from ledgerset path.

    Examples:
        "2025/2025-08.beancount" -> [(2025-08-01, 2025-08-31)]
        "2025/" -> [(2025-01-01, 2025-12-31)]
        "2025/2025-08" -> [(2025-08-01, 2025-08-31)]
    """
    import re
    from datetime import datetime, date
    from calendar import monthrange

    date_ranges = []

    # Pattern for year/month file: 2025/2025-08.beancount or 2025/2025-08
    year_month_pattern = r"(\d{4})/(\d{4})-(\d{2})(?:\.beancount)?$"
    match = re.search(year_month_pattern, ledgerset)
    if match:
        dir_year, file_year, month = match.groups()
        year = int(file_year)
        month_num = int(month)

        # Get first and last day of the month
        first_day = date(year, month_num, 1)
        last_day_num = monthrange(year, month_num)[1]
        last_day = date(year, month_num, last_day_num)

        start_datetime = datetime.combine(first_day, datetime.min.time())
        end_datetime = datetime.combine(last_day, datetime.max.time())

        date_ranges.append((start_datetime, end_datetime))
        return date_ranges

    # Pattern for year directory: 2025/ or 2025
    year_pattern = r"(\d{4})/?$"
    match = re.search(year_pattern, ledgerset)
    if match:
        year = int(match.group(1))

        # Entire year range
        start_datetime = datetime(year, 1, 1, 0, 0, 0)
        end_datetime = datetime(year, 12, 31, 23, 59, 59)

        date_ranges.append((start_datetime, end_datetime))
        return date_ranges

    return date_ranges


def _get_transaction_date(transaction: Dict[str, Any]) -> Optional[datetime]:
    """Extract datetime from a transaction."""
    date_str = transaction.get("date")
    if not date_str:
        return None

    try:
        # Handle various date formats
        if isinstance(date_str, str):
            # Try ISO format first
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                # Try date-only format
                from datetime import date

                parsed_date = date.fromisoformat(date_str)
                return datetime.combine(parsed_date, datetime.min.time())
        elif hasattr(date_str, "year"):
            # Already a datetime/date object
            if hasattr(date_str, "hour"):
                return date_str  # type: ignore[no-any-return]
            else:
                return datetime.combine(date_str, datetime.min.time())
    except (ValueError, TypeError):
        pass

    return None


def _transaction_matches_date_ranges(
    transaction_date: datetime, date_ranges: List[Tuple[datetime, datetime]]
) -> bool:
    """Check if a transaction date falls within any of the given date ranges."""
    for start_date, end_date in date_ranges:
        if start_date <= transaction_date <= end_date:
            return True
    return False


def _find_rules_file(
    ledger: Optional[Path] = None, rules_path: Optional[Path] = None
) -> Path:
    """Find the rules file based on the provided options using consistent resolution pattern."""
    if rules_path:
        if rules_path.is_dir():
            # If given a directory, use rules.yaml in that directory
            return rules_path / "rules.yaml"
        else:
            # If given a file, use that file directly
            return rules_path

    # Use consistent ledger resolution pattern
    if ledger is None:
        ledger_path, _ = handle_default_ledger(None)
    else:
        ledger_path = ledger

    # Rules file has same name as ledger file but with .rules extension
    if ledger_path.is_file() or ledger_path.suffix in [".beancount", ".bean"]:
        rules_file = ledger_path.with_suffix(".rules")
    else:
        # For directory-based ledgers, use rules.yaml in the directory
        rules_file = ledger_path / "rules.yaml"

    return rules_file
