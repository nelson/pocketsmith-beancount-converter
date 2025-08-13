"""Rule management commands for the CLI."""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import typer
import yaml
from dotenv import load_dotenv

from ..pocketsmith.common import PocketSmithClient
from ..rules.loader import RuleLoader
from ..rules.transformer import RuleTransformer
from ..rules.matcher import RuleMatcher
from .changelog import ChangelogManager, determine_changelog_path
from .file_handler import find_default_beancount_file, FileHandlerError


def rule_add_command(if_params: List[str], then_params: List[str]) -> None:
    """Add a new transaction processing rule."""
    try:
        # Parse preconditions
        preconditions = _parse_rule_params(if_params, "precondition")
        transforms = _parse_rule_params(then_params, "transform")

        # Find rules file
        rules_file = _find_rules_file()

        # Load existing rules to determine next ID
        rule_loader = RuleLoader()
        result = rule_loader.load_rules(str(rules_file))
        existing_rules = result.rules

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

        rules_data.append(new_rule_data)

        # Write back to file
        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)

        typer.echo(f"Added rule {next_id} to {rules_file}")

    except Exception as e:
        typer.echo(f"Error adding rule: {e}", err=True)
        raise typer.Exit(1)


def rule_remove_command(rule_id: int) -> None:
    """Remove a transaction processing rule by marking it as disabled."""
    try:
        # Find rules file
        rules_file = _find_rules_file()

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
    rule_id: int, transaction_id: str, dry_run: bool = False
) -> None:
    """Apply a specific rule to a specific transaction."""
    load_dotenv()

    try:
        # Find rules file
        rules_file = _find_rules_file()

        # Load rules
        rule_loader = RuleLoader()
        result = rule_loader.load_rules(str(rules_file))
        rules = result.rules

        # Find the specific rule
        target_rule = None
        for rule in rules:
            if rule.id == rule_id:
                target_rule = rule
                break

        if target_rule is None:
            typer.echo(f"Error: Rule {rule_id} not found", err=True)
            raise typer.Exit(1)

        # Connect to PocketSmith API
        client = PocketSmithClient()

        # Get the transaction
        try:
            transaction = client.get_transaction(int(transaction_id))
        except Exception as e:
            typer.echo(f"Error fetching transaction {transaction_id}: {e}", err=True)
            raise typer.Exit(1)

        # Check if rule matches transaction
        matcher = RuleMatcher()
        matcher.prepare_rules([target_rule])

        match_result = matcher.find_matching_rule(transaction, [target_rule])

        if match_result is None:
            typer.echo(f"Rule {rule_id} does not match transaction {transaction_id}")
            return

        rule, matches = match_result

        if not dry_run:
            # Set up changelog
            beancount_file = find_default_beancount_file()
            single_file = beancount_file.is_file()
            changelog_path = determine_changelog_path(beancount_file, single_file)
            changelog = ChangelogManager(changelog_path)

            # Get categories for transformer
            categories = client.get_categories()

            # Apply the rule
            transformer = RuleTransformer(categories, changelog)
            applications = transformer.apply_transform(
                transaction, rule.transform, rule.id, matches
            )

            # Write back to PocketSmith
            for app in applications:
                if app.status.value == "SUCCESS" and not app.has_warning:
                    try:
                        client.update_transaction(transaction_id, transaction)
                        break  # Success
                    except Exception as e:
                        typer.echo(
                            f"Error updating transaction in PocketSmith: {e}", err=True
                        )

            # Log the application
            for app in applications:
                if app.status.value == "SUCCESS":
                    timestamp = datetime.now().strftime("%b %d %H:%M:%S.%f")[:-3]
                    typer.echo(
                        f"[{timestamp}] APPLY {app.transaction_id} RULE {app.rule_id} {app.field_name} {app.new_value}"
                    )
        else:
            # Dry run - just show what would happen
            # Get categories for transformer but no changelog
            categories = client.get_categories()
            transformer = RuleTransformer(categories, None)
            transaction_copy = transaction.copy()
            applications = transformer.apply_transform(
                transaction_copy, rule.transform, rule.id, matches
            )

            typer.echo(
                f"Dry run - would apply rule {rule_id} to transaction {transaction_id}:"
            )
            for app in applications:
                if app.status.value == "SUCCESS":
                    timestamp = datetime.now().strftime("%b %d %H:%M:%S.%f")[:-3]
                    typer.echo(
                        f"[{timestamp}] APPLY {app.transaction_id} RULE {app.rule_id} {app.field_name} {app.new_value}"
                    )

    except Exception as e:
        typer.echo(f"Error applying rule: {e}", err=True)
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


def _find_rules_file() -> Path:
    """Find the rules file based on the current beancount file."""
    try:
        beancount_file = find_default_beancount_file()
        # Rules file has same name as beancount file but with .rules extension
        rules_file = beancount_file.with_suffix(".rules")
        return rules_file
    except FileHandlerError:
        # Fallback to rules.yaml in current directory
        return Path("rules.yaml")
