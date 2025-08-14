from pathlib import Path
from typing import Any, Dict, List, Optional

from src.cli.push import push_command
from src.cli.date_options import DateOptions
from src.cli.changelog import determine_changelog_path


class FakeClient:
    def __init__(self) -> None:
        self.updated: List[Dict[str, Any]] = []

    def get_user(self) -> Dict[str, Any]:
        return {"login": "tester"}

    def get_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
        updated_since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        # Remote has empty note and no labels; category is id 123
        return [
            {
                "id": 1001,
                "amount": -10.00,
                "date": "2024-01-20T00:00:00Z",
                "currency_code": "USD",
                "merchant": "Coffee Shop",
                "payee": "Coffee Shop",
                "note": "",
                "labels": [],
                "category": {"id": 123, "title": "Coffee"},
                "transaction_account": {
                    "id": 77,
                    "name": "Everyday",
                    "type": "bank",
                    "institution": {"title": "Bank"},
                    "currency_code": "USD",
                },
            }
        ]

    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any], dry_run: bool = False
    ) -> bool:
        self.updated.append(
            {"transaction_id": transaction_id, "updates": updates, "dry_run": dry_run}
        )
        return True

    def get_transaction(self, transaction_id: int) -> Dict[str, Any]:
        return self.get_transactions()[0]


def write_single_file_ledger(path: Path) -> None:
    # Minimal single-file ledger with category declaration and one transaction
    content = "\n".join(
        [
            "; PocketSmith to Beancount - Main File",
            "2024-01-01 commodity USD",
            "2024-01-01 open Assets:Bank:Everyday USD\n    id: 77",
            "2024-01-01 open Expenses:Coffee\n    id: 123",
            "",
            '2024-01-20 * "Coffee Shop" "morning latte" #coffee',
            "    id: 1001",
            "  Expenses:Coffee  10 USD",
            "  Assets:Bank:Everyday  -10 USD",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def test_push_writes_changelog_and_updates_remote(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ledger_path = tmp_path / "ledger.beancount"
    write_single_file_ledger(ledger_path)

    # Monkeypatch client used inside push module
    fake_client = FakeClient()
    monkeypatch.setattr("src.cli.push.PocketSmithClient", lambda: fake_client)

    # Run push (not dry-run) so changelog is written
    push_command(
        destination=ledger_path,
        date_options=DateOptions(),
        dry_run=False,
        verbose=True,
        quiet=True,
        transaction_id=None,
    )

    # Verify update called with expected local-preferred values
    assert len(fake_client.updated) == 1
    update = fake_client.updated[0]
    assert update["transaction_id"] == "1001"
    # Expect note, labels and possibly category_id from local (note present, labels ["coffee"])
    assert update["updates"]["note"] == "morning latte"
    assert update["updates"]["labels"] == ["coffee"]
    # Category id should be preserved as 123 per local mapping
    assert update["updates"]["category_id"] == 123

    # Verify changelog written
    changelog_path = determine_changelog_path(ledger_path, True)
    assert changelog_path.exists()
    log = changelog_path.read_text(encoding="utf-8")
    assert " PUSH " in log
    assert " UPDATE 1001 " in log


def test_push_dry_run_does_not_write_changelog(
    tmp_path: Path, monkeypatch: Any
) -> None:
    ledger_path = tmp_path / "ledger.beancount"
    write_single_file_ledger(ledger_path)

    fake_client = FakeClient()
    monkeypatch.setattr("src.cli.push.PocketSmithClient", lambda: fake_client)

    push_command(
        destination=ledger_path,
        date_options=DateOptions(),
        dry_run=True,
        verbose=False,
        quiet=True,
        transaction_id=None,
    )

    # Dry run still collects differences and attempts updates in dry-run mode
    assert len(fake_client.updated) == 1
    assert fake_client.updated[0]["dry_run"] is True

    changelog_path = determine_changelog_path(ledger_path, True)
    assert not changelog_path.exists()
