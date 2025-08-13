"""Exercise RuleTransformer.log_applications branches for coverage."""

from src.rules.models import (
    RuleApplication,
    RuleApplicationStatus,
)
from src.rules.transformer import RuleTransformer


class DummyChangelog:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def log_entry(self, text: str) -> None:
        self.entries.append(text)


def test_log_applications_success_and_warning_and_labels():
    cl = DummyChangelog()
    transformer = RuleTransformer(categories=[], changelog=cl)

    # Success without warning (CATEGORY)
    apps = [
        RuleApplication(
            rule_id=1,
            transaction_id="t1",
            field_name="CATEGORY",
            old_value="Old",
            new_value="New",
            status=RuleApplicationStatus.SUCCESS,
        ),
        # Success with warning (MEMO)
        RuleApplication(
            rule_id=1,
            transaction_id="t2",
            field_name="MEMO",
            old_value="a",
            new_value="b",
            status=RuleApplicationStatus.SUCCESS,
            warning_message="overwrite",
        ),
        # Labels special formatting with added/removed
        RuleApplication(
            rule_id=2,
            transaction_id="t3",
            field_name="LABELS",
            old_value=["x", "y"],
            new_value=["y", "z"],
            status=RuleApplicationStatus.SUCCESS,
        ),
    ]

    transformer.log_applications(apps)
    # Should produce 3 log entries
    assert len(cl.entries) == 3
    assert any("CATEGORY New" in e for e in cl.entries)
    assert any("OVERWRITE MEMO" in e for e in cl.entries)
    assert any("+z -x" in e or "-x +z" in e for e in cl.entries)


def test_log_applications_invalid_and_error():
    cl = DummyChangelog()
    transformer = RuleTransformer(categories=[], changelog=cl)

    apps = [
        RuleApplication(
            rule_id=3,
            transaction_id="t4",
            field_name="CATEGORY",
            old_value="Old",
            new_value="Missing",
            status=RuleApplicationStatus.INVALID,
        ),
        RuleApplication(
            rule_id=4,
            transaction_id="t5",
            field_name="MEMO",
            old_value="",
            new_value="",
            status=RuleApplicationStatus.ERROR,
            error_message="boom",
        ),
    ]

    transformer.log_applications(apps)
    assert any("INVALID CATEGORY" in e for e in cl.entries)
    assert any("ERROR MEMO boom" in e for e in cl.entries)
