"""Integration-ish test covering RuleCLI.handle_apply_command in dry-run mode."""

from types import SimpleNamespace
import yaml

from src.rules.cli import RuleCLI


def test_handle_apply_command_dry_run(tmp_path):
    # Create rules.yaml with one rule
    rules_path = tmp_path / "rules.yaml"
    yaml.safe_dump(
        [{"id": 1, "if": [{"merchant": "Shop"}], "then": [{"memo": "Buy"}]}],
        rules_path.open("w"),
    )

    # Prepare transactions and categories
    transactions = [{"id": 10, "payee": "Shop", "labels": []}]
    categories: list[dict] = []

    # Args namespace
    args = SimpleNamespace(
        rules_file=str(rules_path),
        transaction_ids=None,
        output_dir=str(tmp_path),
        dry_run=True,
    )

    cli = RuleCLI()
    cli.handle_apply_command(args, transactions, categories)
