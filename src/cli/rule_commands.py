"""Rule management commands for the CLI."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import typer
import yaml
from dotenv import load_dotenv

from ..pocketsmith.common import PocketSmithClient
from ..rules.loader import RuleLoader
from ..rules.transformer import RuleTransformer
from ..rules.matcher import RuleMatcher
from .changelog import ChangelogManager, determine_changelog_path
from .file_handler import find_default_beancount_file, FileHandlerError


def rule_add_command(
    if_params: List[str],
    then_params: List[str],
    destination: Optional[Path] = None,
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
            rules_file = _find_rules_file(destination, rules_path)

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

        # Write back to file
        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)

        typer.echo(f"Added rule {next_id} to {rules_file}")

    except Exception as e:
        typer.echo(f"Error adding rule: {e}", err=True)
        raise typer.Exit(1)


def rule_remove_command(rule_id: int, rules_path: Optional[Path] = None) -> None:
    """Remove a transaction processing rule by marking it as disabled."""
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

        # Write back to file
        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)

        typer.echo(f"Disabled rule {rule_id}")

    except Exception as e:
        typer.echo(f"Error removing rule: {e}", err=True)
        raise typer.Exit(1)


def rule_apply_command(
    rule_id: Optional[int],
    transaction_id: Optional[str],
    dry_run: bool = False,
    destination: Optional[Path] = None,
    rules_path: Optional[Path] = None,
) -> None:
    """Apply rules to transactions.

    If rule_id is not provided, all rules will be eligible for evaluation.
    If transaction_id is not provided, all transactions will be matched against eligible rules.
    """
    load_dotenv()

    try:
        # Determine rules path for loading
        if rules_path:
            # Use the rules path directly (can be file or directory)
            rules_load_path = rules_path
        else:
            # Find rules file using the existing logic
            rules_load_path = _find_rules_file(destination, rules_path)

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

        # Determine eligible rules
        if rule_id is not None:
            # Find the specific rule
            eligible_rules = [rule for rule in all_rules if rule.id == rule_id]
            if not eligible_rules:
                typer.echo(f"Error: Rule {rule_id} not found", err=True)
                raise typer.Exit(1)
        else:
            # All rules are eligible
            eligible_rules = all_rules

        # Connect to PocketSmith API
        client = PocketSmithClient()

        # Get transactions
        transactions = []
        if transaction_id is not None:
            # Get specific transaction
            try:
                transaction = client.get_transaction(int(transaction_id))
                transactions = [transaction]
            except Exception as e:
                typer.echo(
                    f"Error fetching transaction {transaction_id}: {e}", err=True
                )
                raise typer.Exit(1)
        else:
            # Get all transactions - use last sync info or reasonable defaults
            try:
                if destination:
                    beancount_file = destination
                else:
                    beancount_file = find_default_beancount_file()
                single_file = beancount_file.is_file()
                changelog_path = determine_changelog_path(beancount_file, single_file)
                temp_changelog = ChangelogManager(changelog_path)

                # Try to get date range from last sync
                last_sync_info = temp_changelog.get_last_sync_info()
                if last_sync_info:
                    _, from_date, to_date = last_sync_info
                    transactions = client.get_transactions(
                        start_date=from_date,
                        end_date=to_date,
                    )
                else:
                    # No sync info, get recent transactions (last 30 days)
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    transactions = client.get_transactions(
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )
            except Exception as e:
                typer.echo(f"Error fetching transactions: {e}", err=True)
                raise typer.Exit(1)

        if not transactions:
            typer.echo("No transactions to process")
            return

        if not eligible_rules:
            typer.echo("No rules to apply")
            return

        # Set up transformation infrastructure
        categories = client.get_categories()

        changelog: Optional[ChangelogManager] = None
        if not dry_run:
            if destination:
                beancount_file = destination
            else:
                beancount_file = find_default_beancount_file()
            single_file = beancount_file.is_file()
            changelog_path = determine_changelog_path(beancount_file, single_file)
            changelog = ChangelogManager(changelog_path)

        transformer = RuleTransformer(categories, changelog)
        matcher = RuleMatcher()
        matcher.prepare_rules(eligible_rules)

        # Apply rules to transactions
        total_applications = 0
        total_matches = 0

        for transaction in transactions:
            # Find first matching rule for this transaction
            match_result = matcher.find_matching_rule(transaction, eligible_rules)

            if match_result:
                rule, matches = match_result
                total_matches += 1

                if dry_run:
                    typer.echo(
                        f"Would apply rule {rule.id} to transaction {transaction.get('id')}"
                    )

                    # Show what would change
                    transaction_copy = transaction.copy()
                    applications = transformer.apply_transform(
                        transaction_copy, rule.transform, rule.id, matches
                    )

                    for app in applications:
                        if app.status.value == "SUCCESS":
                            timestamp = datetime.now().strftime("%b %d %H:%M:%S.%f")[
                                :-3
                            ]
                            typer.echo(
                                f"[{timestamp}] APPLY {app.transaction_id} RULE {app.rule_id} {app.field_name} {app.new_value}"
                            )
                            total_applications += 1
                else:
                    # Apply the transformation
                    applications = transformer.apply_transform(
                        transaction, rule.transform, rule.id, matches
                    )

                    # Write back to PocketSmith
                    for app in applications:
                        if app.status.value == "SUCCESS" and not app.has_warning:
                            try:
                                client.update_transaction(
                                    str(transaction.get("id")), transaction
                                )
                                break  # Success
                            except Exception as e:
                                typer.echo(
                                    f"Error updating transaction {transaction.get('id')} in PocketSmith: {e}",
                                    err=True,
                                )

                    # Log successful applications
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

                            timestamp = datetime.now().strftime("%b %d %H:%M:%S.%f")[
                                :-3
                            ]
                            typer.echo(
                                f"[{timestamp}] APPLY {app.transaction_id} RULE {app.rule_id} {app.field_name} {app.new_value}"
                            )

        # Print summary
        rules_desc = f"rule {rule_id}" if rule_id else f"{len(eligible_rules)} rules"
        transactions_desc = (
            f"transaction {transaction_id}"
            if transaction_id
            else f"{len(transactions)} transactions"
        )

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


def _find_rules_file(
    destination: Optional[Path] = None, rules_path: Optional[Path] = None
) -> Path:
    """Find the rules file based on the provided options or current beancount file."""
    if rules_path:
        if rules_path.is_dir():
            # If given a directory, use rules.yaml in that directory
            return rules_path / "rules.yaml"
        else:
            # If given a file, use that file directly
            return rules_path

    try:
        if destination:
            beancount_file = destination
        else:
            beancount_file = find_default_beancount_file()

        # Rules file has same name as beancount file but with .rules extension
        rules_file = beancount_file.with_suffix(".rules")
        return rules_file
    except FileHandlerError:
        # Fallback to rules.yaml in current directory
        return Path("rules.yaml")
