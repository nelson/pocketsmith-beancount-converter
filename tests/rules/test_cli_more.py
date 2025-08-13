"""Extra small tests to cover RuleCLI handle_add_rule_command branches."""

from types import SimpleNamespace

from src.rules.cli import RuleCLI


def test_handle_add_rule_command_branches(monkeypatch):
    cli = RuleCLI()

    called = {"interactive": False, "args": False}

    def fake_interactive():
        called["interactive"] = True

    def fake_from_args(args):
        called["args"] = True

    monkeypatch.setattr(cli, "_add_rule_interactive", fake_interactive)
    monkeypatch.setattr(cli, "_add_rule_from_args", fake_from_args)

    cli.handle_add_rule_command(SimpleNamespace(interactive=True))
    cli.handle_add_rule_command(SimpleNamespace(interactive=False))

    assert called["interactive"] and called["args"]
