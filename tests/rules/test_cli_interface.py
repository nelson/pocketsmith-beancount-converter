"""Tests for rules.cli RuleCLI helper behaviors.

Covers description rendering and summary printing without touching interactive paths.
"""

from types import SimpleNamespace
import pytest

from src.rules.cli import RuleCLI
from src.rules.models import (
    RuleApplication,
    RuleApplicationBatch,
    RuleApplicationStatus,
    RuleTransform,
)


def test_describe_transform_variants():
    cli = RuleCLI()

    # Only category
    t1 = RuleTransform(category="Dining")
    assert cli._describe_transform(t1) == "category → Dining"

    # Labels and memo
    t2 = RuleTransform(labels=["a", "b"], memo="hello")
    desc2 = cli._describe_transform(t2)
    assert "labels → a, b" in desc2
    assert "memo → hello" in desc2

    # Metadata
    t3 = RuleTransform(metadata={"k": "v", "x": 1})
    desc3 = cli._describe_transform(t3)
    assert "metadata →" in desc3
    assert "k=v" in desc3 and "x=1" in desc3

    # Nothing
    t4 = RuleTransform(labels=["z"])  # ensure not empty
    # strip labels to test empty visual (remove in-place)
    t4.labels = None
    t4.category = None
    t4.memo = None
    t4.metadata = None
    assert cli._describe_transform(t4) == "no changes"


def test_print_application_results_summary(capsys):
    cli = RuleCLI()
    batch = RuleApplicationBatch()
    batch.rules_loaded = 2
    batch.transactions_processed = 3

    # Success
    batch.add_application(
        RuleApplication(
            rule_id=1,
            transaction_id="t1",
            field_name="CATEGORY",
            old_value="Old",
            new_value="New",
            status=RuleApplicationStatus.SUCCESS,
        )
    )
    # Invalid
    batch.add_application(
        RuleApplication(
            rule_id=2,
            transaction_id="t2",
            field_name="CATEGORY",
            old_value="Old",
            new_value="Missing",
            status=RuleApplicationStatus.INVALID,
            error_message="Category not found",
        )
    )
    # Warning
    batch.add_application(
        RuleApplication(
            rule_id=1,
            transaction_id="t3",
            field_name="MEMO",
            old_value="old",
            new_value="new",
            status=RuleApplicationStatus.SUCCESS,
            warning_message="overwrite",
        )
    )

    cli._print_application_results(batch, dry_run=False)
    out = capsys.readouterr().out
    assert "Rules loaded: 2" in out
    assert "Transactions processed: 3" in out
    assert "Successful applications:" in out
    assert "Failed Applications:" in out
    assert "Warnings:" in out


def test_add_rule_from_args_writes_file(tmp_path):
    cli = RuleCLI()
    out_file = tmp_path / "rules.yaml"

    args = SimpleNamespace(
        rule_id=10,
        account="acct.*",
        category=None,
        merchant=None,
        new_category="Dining",
        labels="tag1,tag2",
        memo=None,
        metadata="k=v,x=y",
        output_file=str(out_file),
        interactive=False,
    )

    # Should not raise and should write YAML
    cli._add_rule_from_args(args)
    assert out_file.exists()
    content = out_file.read_text()
    assert "- id: 10" in content
    assert "account:" in content and "Dining" in content
    assert "labels:" in content and "tag1" in content

    # Call again to exercise newline branch when appending to existing file
    cli._add_rule_from_args(args)


def test_add_rule_from_args_validation_errors(tmp_path):
    cli = RuleCLI()
    # Missing conditions
    bad_args1 = SimpleNamespace(
        rule_id=11,
        account=None,
        category=None,
        merchant=None,
        new_category="X",
        labels=None,
        memo=None,
        metadata=None,
        output_file=str(tmp_path / "rules.yaml"),
        interactive=False,
    )
    with pytest.raises(SystemExit):
        cli._add_rule_from_args(bad_args1)

    # Missing transforms
    bad_args2 = SimpleNamespace(
        rule_id=12,
        account="acc",
        category=None,
        merchant=None,
        new_category=None,
        labels=None,
        memo=None,
        metadata=None,
        output_file=str(tmp_path / "rules.yaml"),
        interactive=False,
    )
    with pytest.raises(SystemExit):
        cli._add_rule_from_args(bad_args2)


def test_create_rule_yaml_single_label_and_merchant():
    cli = RuleCLI()
    yaml_text = cli._create_rule_yaml(
        5,
        account=None,
        category=None,
        merchant="M",
        new_category=None,
        labels=["l"],
        memo=None,
        metadata=None,
    )
    assert 'merchant: "M"' in yaml_text
    assert 'labels: "l"' in yaml_text


def test_handle_apply_command_filters_transactions(tmp_path, capsys):
    # Prepare a rules file and args with transaction_ids filter
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        '- id: 1\n  if:\n    - merchant: "Shop"\n  then:\n    - memo: "M"\n'
    )

    cli = RuleCLI()
    transactions = [
        {"id": 1, "payee": "Shop", "labels": []},
        {"id": 2, "payee": "Other", "labels": []},
    ]
    categories: list[dict] = []
    args = type(
        "Args",
        (),
        {
            "rules_file": str(rules_path),
            "transaction_ids": [1],
            "output_dir": str(tmp_path),
            "dry_run": True,
        },
    )()

    cli.handle_apply_command(args, transactions, categories)
    out = capsys.readouterr().out
    assert "Filtered to 1 specific transactions" in out
