"""Unit tests for src.cli.rule_commands helpers and flows.

Network and file system heavy parts are mocked/stubbed to keep tests fast.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import yaml

from src.cli import rule_commands as rc


def test_parse_rule_params_basic_and_metadata():
    # Basic key=value
    out = rc._parse_rule_params(
        ["merchant=Starbucks", "category=Dining"], "precondition"
    )
    assert out["merchant"] == "Starbucks"
    assert out["category"] == "Dining"

    # Unknown keys become metadata for preconditions
    out2 = rc._parse_rule_params(["custom_key=123"], "precondition")
    assert out2["metadata"]["custom_key"] == "123"

    # Error cases are exercised in CLI E2E; keep unit tests to non-exit paths


def test_convert_preconditions_and_transforms_yaml():
    pre = {"account": "acc.*", "metadata": {"k": "v"}}
    pre_yaml = rc._convert_preconditions_to_yaml(pre)
    # order not guaranteed but both entries present
    assert any("account" in d for d in pre_yaml)
    assert any("metadata" in d for d in pre_yaml)

    trans = {"category": "Dining", "memo": "hi", "custom": "x"}
    trans_yaml = rc._convert_transforms_to_yaml(trans)
    # custom should be collected under metadata
    assert any("metadata" in d for d in trans_yaml)
    assert any("category" in d for d in trans_yaml)
    assert any("memo" in d for d in trans_yaml)


def test_find_rules_file_fallback_when_no_beancount(monkeypatch, tmp_path):
    # make cwd temp
    monkeypatch.chdir(tmp_path)
    # Simulate FileHandlerError from find_default_beancount_file
    monkeypatch.setattr(
        rc,
        "find_default_beancount_file",
        lambda: (_ for _ in ()).throw(rc.FileHandlerError("no file")),
    )
    path = rc._find_rules_file()
    assert path == Path("rules.yaml")


def test_rule_add_command_appends_yaml(tmp_path, monkeypatch):
    # Arrange rules file target via fallback
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        rc,
        "find_default_beancount_file",
        lambda: (_ for _ in ()).throw(rc.FileHandlerError("no file")),
    )

    # Stub RuleLoader.load_rules to simulate existing rules
    class DummyResult:
        def __init__(self) -> None:
            self.rules = [SimpleNamespace(id=1)]

    dummy_loader = MagicMock()
    dummy_loader.load_rules.return_value = DummyResult()
    monkeypatch.setattr(rc, "RuleLoader", lambda: dummy_loader)

    rc.rule_add_command(["merchant=Test"], ["category=Dining"])

    # Verify contents
    data = yaml.safe_load(Path("rules.yaml").read_text())
    assert isinstance(data, list)
    assert any(rule["id"] == 2 for rule in data)


def test_rule_remove_command_marks_disabled(tmp_path, monkeypatch):
    # Prepare a rules file
    monkeypatch.chdir(tmp_path)
    rules_path = tmp_path / "rules.yaml"
    yaml.safe_dump(
        [{"id": 3, "if": [{"merchant": "A"}], "then": [{"memo": "M"}]}],
        rules_path.open("w"),
    )

    # Ensure _find_rules_file returns this file
    monkeypatch.setattr(rc, "_find_rules_file", lambda *args, **kwargs: rules_path)

    rc.rule_remove_command(3)
    data = yaml.safe_load(rules_path.read_text())
    assert data[0]["disabled"] is True


def test_rule_apply_command_dry_run_path(monkeypatch, tmp_path, capsys):
    # Create a simple rules file
    monkeypatch.chdir(tmp_path)
    rules_path = tmp_path / "rules.yaml"
    yaml.safe_dump(
        [
            {
                "id": 5,
                "if": [{"merchant": "Test"}],
                "then": [{"memo": "Hello"}],
            }
        ],
        rules_path.open("w"),
    )

    # Make loader return this rule
    from src.rules.loader import RuleLoader as RealRuleLoader

    real_loader = RealRuleLoader()
    monkeypatch.setattr(rc, "RuleLoader", lambda: real_loader)
    monkeypatch.setattr(rc, "_find_rules_file", lambda *args, **kwargs: rules_path)

    # Fake client with get_categories and get_transactions
    class DummyClient:
        def get_categories(self) -> list[dict]:
            return [{"id": 1, "title": "Dining"}]

        def get_transactions(
            self, start_date: str = None, end_date: str = None
        ) -> list[dict[str, object]]:
            return [{"id": "123", "payee": "Test", "labels": []}]

    # Mock local beancount reading instead of PocketSmith API
    def mock_read_transactions_for_rules(*args):
        return [
            {
                "id": "123",
                "payee": "Test",
                "labels": [],
                "category": None,
                "date": "2023-01-01",
                "narration": "",
            }
        ]

    monkeypatch.setattr(
        rc, "_read_transactions_for_rules", mock_read_transactions_for_rules
    )

    # Create a dummy changelog to handle the new date logic
    class DummyChangelog:
        def get_last_sync_info(self):
            return None

    monkeypatch.setattr(
        rc, "find_default_beancount_file", lambda: tmp_path / "ledger.beancount"
    )
    monkeypatch.setattr(
        rc, "determine_changelog_path", lambda base, single: tmp_path / "main.log"
    )
    monkeypatch.setattr(rc, "ChangelogManager", lambda path: DummyChangelog())

    # Run dry run
    rc.rule_apply_command(ruleset=5, dry_run=True)
    out = capsys.readouterr().out
    assert "Would apply rule 5 to transaction 123" in out
    assert "Dry run completed:" in out
