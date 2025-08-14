from pathlib import Path
from src.cli.changelog import ChangelogManager


def test_write_push_entry(tmp_path: Path) -> None:
    log_path = tmp_path / "main.log"
    mgr = ChangelogManager(log_path)

    mgr.write_push_entry("2024-01-01", "2024-01-31")

    content = log_path.read_text(encoding="utf-8").strip()
    # Format: [timestamp] PUSH 2024-01-01 2024-01-31
    assert content.endswith(" PUSH 2024-01-01 2024-01-31")
