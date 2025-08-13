"""Additional coverage for RuleMatcher utilities."""

from src.rules.matcher import RuleMatcher
from src.rules.models import RulePrecondition, RuleTransform, TransactionRule


def test_parse_metadata_and_groups_and_substitution():
    matcher = RuleMatcher()

    # Prepare a rule with groups
    rule = TransactionRule(
        id=1,
        precondition=RulePrecondition(merchant=r"ACME (.+)", account=r"Cash (\d+)"),
        transform=RuleTransform(memo="Order \\1 to {account.1}"),
    )

    matcher.prepare_rules([rule])
    # Extract fields from transaction notes including metadata
    txn = {
        "payee": "ACME Corp",
        "account": {"name": "Cash 12", "type": "bank"},
        "notes": "k: v, ref: 99",
    }
    fields = matcher._extract_transaction_fields(txn)
    assert fields["merchant"] == "ACME Corp"
    assert fields["account"] == "Cash 12"
    assert fields["metadata.k"] == "v"

    # Match rule
    matched = matcher._match_rule(rule, fields)
    assert matched is not None
    groups = matcher.get_match_groups(matched)
    # merchant group 1 should exist
    assert "merchant" in groups

    # Substitution: both \1 and {account.1}
    text = matcher.substitute_groups_in_text("Order \\1 to {account.1}", matched)
    # \\1 uses the first available group's capture (from account here)
    assert text == "Order 12 to 12"

    # Simple validate utility
    assert matcher.validate_transaction_for_matching(txn) is True
    matcher.clear_compiled_patterns()
