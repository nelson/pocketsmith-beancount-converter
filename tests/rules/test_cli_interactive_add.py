"""Cover interactive rule addition path in rules.cli."""

from unittest.mock import patch

from src.rules.cli import RuleCLI


def test_add_rule_interactive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Simulate user inputs: id, account blank, category 'Food', merchant blank,
    # transforms: new_category blank, labels "a,b", memo "m", metadata "k=v"
    inputs = iter(
        [
            "1",  # id
            "",  # account
            "Food",  # category
            "",  # merchant
            "",  # new_category
            "a,b",  # labels
            "m",  # memo
            "k=v",  # metadata
            "rules.yaml",  # output file
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    cli = RuleCLI()
    with patch("builtins.input", fake_input):
        cli._add_rule_interactive()

    out = (tmp_path / "rules.yaml").read_text()
    assert "- id: 1" in out
    assert "labels:" in out and "- a" in out


def test_add_rule_interactive_no_conditions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = iter(
        [
            "2",  # id
            "",  # account
            "",  # category
            "",  # merchant -> triggers early return
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    cli = RuleCLI()
    with patch("builtins.input", fake_input):
        cli._add_rule_interactive()
    # No file created since early return
    assert not (tmp_path / "rules.yaml").exists()


def test_add_rule_interactive_no_transforms(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = iter(
        [
            "3",  # id
            "Acc",  # account
            "",  # category
            "",  # merchant
            "",  # new_category
            "",  # labels
            "",  # memo
            "",  # metadata -> triggers no transforms branch
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    cli = RuleCLI()
    with patch("builtins.input", fake_input):
        cli._add_rule_interactive()
    # No file created since early return
    assert not (tmp_path / "rules.yaml").exists()


def test_add_rule_interactive_id_validation_loop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = iter(
        [
            "0",  # invalid: not positive -> message then ask again
            "abc",  # invalid: ValueError -> message then ask again
            "4",  # valid id
            "Acc",  # account
            "",  # category
            "",  # merchant
            "Cat",  # new_category
            "",  # labels
            "",  # memo
            "",  # metadata
            "rules.yaml",  # out
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    cli = RuleCLI()
    with patch("builtins.input", fake_input):
        cli._add_rule_interactive()
    # File written
    assert (tmp_path / "rules.yaml").exists()


def test_add_rule_interactive_keyboard_interrupt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_input(prompt: str = "") -> str:
        raise KeyboardInterrupt()

    cli = RuleCLI()
    with patch("builtins.input", fake_input):
        # Should handle KeyboardInterrupt gracefully (no exception)
        cli._add_rule_interactive()
