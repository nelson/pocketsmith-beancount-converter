"""Test RuleCLI._apply_rules_to_transactions non-dry-run path."""

from src.rules.cli import RuleCLI
from src.rules.models import RulePrecondition, RuleTransform, TransactionRule


class DummyChangelog:
    def __init__(self) -> None:
        self.logged = []

    def log_entry(self, text: str) -> None:
        self.logged.append(text)


def test_apply_rules_to_transactions_non_dry():
    cli = RuleCLI()
    rules = [
        TransactionRule(
            id=1,
            precondition=RulePrecondition(merchant=r"Shop"),
            transform=RuleTransform(memo="X", labels=["a"]),
        )
    ]

    txns = [{"id": 1, "payee": "Shop", "labels": []}]
    batch = cli._apply_rules_to_transactions(
        txns, rules, categories=[], changelog=DummyChangelog(), dry_run=False
    )

    # Applications recorded for each field (labels + memo)
    assert batch.transactions_matched >= 1
    assert batch.success_count >= 1
