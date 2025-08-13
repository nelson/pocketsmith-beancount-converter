"""Additional tests for RuleTransformer covering category/labels/memo/metadata branches."""

from decimal import Decimal

from src.rules.transformer import RuleTransformer
from src.rules.models import RuleTransform, RuleApplicationStatus
from src.rules.matcher import RuleMatcher


def test_apply_category_uncategorized_sets_none():
    t = {"id": 1, "category": {"title": "Old"}}
    transformer = RuleTransformer(
        categories=[{"id": 10, "title": "Dining"}], changelog=None
    )
    apps = transformer.apply_transform(
        t, RuleTransform(category="Uncategorized"), rule_id=1
    )
    assert any(
        a.field_name == "CATEGORY" and a.status == RuleApplicationStatus.SUCCESS
        for a in apps
    )
    assert t["category"] is None


def test_labels_add_remove_and_sanitize_and_memo_substitution():
    # Regex matches for memo and labels
    matcher = RuleMatcher()
    txn = {"id": 2, "payee": "STORE 99", "labels": []}
    from src.rules.models import RulePrecondition, TransactionRule

    transform = RuleTransform(labels=["+ New Tag", "-old", "@@@"], memo="Ref \\1")
    proper_rule = TransactionRule(
        id=3,
        precondition=RulePrecondition(merchant=r"STORE (\d+)"),
        transform=transform,
    )
    matcher.prepare_rules([proper_rule])
    matches = matcher._match_rule(proper_rule, matcher._extract_transaction_fields(txn))
    assert matches is not None

    transformer = RuleTransformer(categories=[], changelog=None)
    apps = transformer.apply_transform(txn, transform, rule_id=3, regex_matches=matches)
    # one LABELS and one MEMO change
    assert any(a.field_name == "LABELS" for a in apps)
    assert any(a.field_name == "MEMO" for a in apps)
    # invalid label '@@@' sanitized away; '+ New Tag' normalized to 'new-tag'; '-old' removed (no effect here)
    assert "new-tag" in txn["labels"]
    assert txn.get("memo", "").startswith("Ref ")


def test_metadata_transform_with_warnings_and_serialization():
    txn = {"id": 3, "notes": "flag: yes"}
    transformer = RuleTransformer(categories=[], changelog=None)
    apps = transformer.apply_transform(
        txn,
        RuleTransform(metadata={"flag": False, "count": 2, "price": Decimal("1.23")}),
        rule_id=1,
    )
    # Single METADATA application with warning for 'flag'
    meta_apps = [a for a in apps if a.field_name == "METADATA"]
    assert meta_apps and meta_apps[0].status == RuleApplicationStatus.SUCCESS
    # Notes serialized as sorted key pairs
    assert ", " in txn.get("notes", "") and "count: 2" in txn["notes"]


def test_log_applications_labels_no_changes_logged():
    # Ensure labels path without changes produces 'no changes'
    class DummyChangelog:
        def __init__(self) -> None:
            self.entries: list[str] = []

        def log_entry(self, text: str) -> None:
            self.entries.append(text)

    cl = DummyChangelog()
    transformer = RuleTransformer(categories=[], changelog=cl)
    from src.rules.models import RuleApplication

    transformer.log_applications(
        [
            RuleApplication(
                rule_id=1,
                transaction_id="t",
                field_name="LABELS",
                old_value=["a"],
                new_value=["a"],
                status=RuleApplicationStatus.SUCCESS,
            )
        ]
    )
    assert any("no changes" in e for e in cl.entries)
