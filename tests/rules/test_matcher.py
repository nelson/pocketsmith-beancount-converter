"""Tests for rules.matcher module functionality."""

from src.rules.matcher import RuleMatcher
from src.rules.models import RulePrecondition, RuleTransform, TransactionRule


def test_parse_metadata_and_groups_and_substitution():
    matcher = RuleMatcher()

    rule = TransactionRule(
        id=1,
        precondition=RulePrecondition(merchant=r"ACME (.+)", account=r"Cash (\d+)"),
        transform=RuleTransform(memo="Order \\1 to {account.1}"),
    )
    matcher.prepare_rules([rule])
    txn = {
        "payee": "ACME Corp",
        "account": {"name": "Cash 12", "type": "bank"},
        "notes": "k: v, ref: 99",
    }
    fields = matcher._extract_transaction_fields(txn)
    assert fields["merchant"] == "ACME Corp"
    assert fields["account"] == "Cash 12"
    assert fields["metadata.k"] == "v"

    matched = matcher._match_rule(rule, fields)
    assert matched is not None
    groups = matcher.get_match_groups(matched)
    assert "merchant" in groups

    text = matcher.substitute_groups_in_text("Order \\1 to {account.1}", matched)
    assert text == "Order 12 to 12"
    assert matcher.validate_transaction_for_matching(txn) is True
    matcher.clear_compiled_patterns()


def test_prepare_rules_skips_invalid_regex():
    matcher = RuleMatcher()
    bad = TransactionRule(
        id=1,
        precondition=RulePrecondition(merchant="["),
        transform=RuleTransform(memo="x"),
    )
    matcher.prepare_rules([bad])
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
