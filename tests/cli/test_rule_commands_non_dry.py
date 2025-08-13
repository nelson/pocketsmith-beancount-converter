"""Test non-dry-run path in rule_apply_command with dummy client and changelog."""

from pathlib import Path
from typing import Any
import yaml

from src.cli import rule_commands as rc


def test_rule_apply_command_non_dry(monkeypatch, tmp_path):
    # Prepare rules file
    rules_path = tmp_path / "rules.yaml"
    yaml.safe_dump(
        [{"id": 7, "if": [{"merchant": "M"}], "then": [{"memo": "X"}]}],
        rules_path.open("w"),
    )

    # Provide _find_rules_file to return our file
    monkeypatch.setattr(rc, "_find_rules_file", lambda: rules_path)

    # Real loader to parse YAML
    from src.rules.loader import RuleLoader as RealRuleLoader

    monkeypatch.setattr(rc, "RuleLoader", lambda: RealRuleLoader())

    # Dummy client
    class DummyClient:
        def get_categories(self) -> list[dict[str, Any]]:
            return []

        def get_transaction(self, tid: int) -> dict[str, Any]:
            return {"id": tid, "payee": "M", "labels": []}

        def update_transaction(
            self, transaction_id: str, updates: dict[str, Any], dry_run: bool = False
        ) -> bool:
            return True

    monkeypatch.setattr(rc, "PocketSmithClient", lambda: DummyClient())

    # Avoid filesystem complexity in changelog path resolution
    monkeypatch.setattr(rc, "find_default_beancount_file", lambda: tmp_path)
    monkeypatch.setattr(
        rc, "determine_changelog_path", lambda base, single: tmp_path / "main.log"
    )

    # Use a dummy ChangelogManager with minimal interface
    class DummyChangelog:
        def __init__(self, p: Path) -> None: ...

    monkeypatch.setattr(rc, "ChangelogManager", DummyChangelog)

    rc.rule_apply_command(7, "999", dry_run=False)
