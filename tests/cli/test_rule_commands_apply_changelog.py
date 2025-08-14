"""Assert APPLY entries are written to a real changelog file in non-dry mode."""

from pathlib import Path
from typing import Any
import yaml

from src.cli import rule_commands as rc


def test_rule_apply_writes_apply_entries_to_changelog(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # Prepare a simple rules file with one rule (memo transform)
    rules_path = tmp_path / "rules.yaml"
    yaml.safe_dump(
        [{"id": 42, "if": [{"merchant": "M"}], "then": [{"memo": "X"}]}],
        rules_path.open("w"),
    )

    # Make CLI use our rules file
    monkeypatch.setattr(rc, "_find_rules_file", lambda: rules_path)

    # Use real RuleLoader to parse YAML
    from src.rules.loader import RuleLoader as RealRuleLoader

    monkeypatch.setattr(rc, "RuleLoader", lambda: RealRuleLoader())

    # Dummy PocketSmith client used by the command
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

    # Make changelog path resolve to a real file using single-file mode
    ledger_path = tmp_path / "ledger.beancount"
    ledger_path.write_text("; empty ledger", encoding="utf-8")
    monkeypatch.setattr(rc, "find_default_beancount_file", lambda: ledger_path)

    # Run the non-dry apply command
    rc.rule_apply_command(42, "999", dry_run=False)

    # Real changelog file should be created at ledger.beancount.log
    changelog_path = ledger_path.with_suffix(".log")
    assert changelog_path.exists(), "Changelog file should exist"
    content = changelog_path.read_text(encoding="utf-8")

    # Expect an APPLY entry including Rule ID, field key, and new value
    assert "APPLY" in content
    assert "RULE 42" in content
    assert "MEMO" in content or "MEMO" in content.upper()
    assert "X" in content
