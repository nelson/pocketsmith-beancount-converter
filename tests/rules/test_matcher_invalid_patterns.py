"""Ensure invalid regex patterns are safely skipped in prepare_rules."""

from src.rules.matcher import RuleMatcher
from src.rules.models import RulePrecondition, RuleTransform, TransactionRule


def test_prepare_rules_skips_invalid_regex():
    matcher = RuleMatcher()
    bad = TransactionRule(
        id=1,
        precondition=RulePrecondition(merchant="["),  # invalid regex
        transform=RuleTransform(memo="x"),
    )
    matcher.prepare_rules([bad])
    # No compiled patterns stored for invalid rule
    assert matcher._compiled_patterns == {}


def test_prepare_rules_skips_invalid_other_fields():
    matcher = RuleMatcher()
    bads = [
        TransactionRule(
            id=2,
            precondition=RulePrecondition(category="["),
            transform=RuleTransform(memo="x"),
        ),
        TransactionRule(
            id=3,
            precondition=RulePrecondition(account="["),
            transform=RuleTransform(memo="x"),
        ),
        TransactionRule(
            id=4,
            precondition=RulePrecondition(metadata={"k": "["}),
            transform=RuleTransform(memo="x"),
        ),
    ]
    matcher.prepare_rules(bads)
    assert matcher._compiled_patterns == {}
