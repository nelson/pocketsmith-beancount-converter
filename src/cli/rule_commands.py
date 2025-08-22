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

                    # Note: rule apply does not write back to remote PocketSmith data
                    # Write back only happens during pull/push commands

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


def rule_list_command(
    verbose: bool = False,
    rule_id: Optional[str] = None,
    rules_path: Optional[Path] = None,
) -> None:
    """List all rules found."""
    try:
        # Determine rules path for loading
        if rules_path:
            rules_load_path = rules_path
        else:
            # Use default rules path
            rules_load_path = Path(".rules/")

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
                typer.echo(f"RULE {rule.id}")

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

        # Determine rules path for loading
        if rules_path:
            rules_load_path = rules_path
        else:
            # Use default rules path
            rules_load_path = Path(".rules/")

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
