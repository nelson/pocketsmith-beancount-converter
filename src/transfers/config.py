"""Configuration persistence for transfer detection."""

from pathlib import Path
from typing import Optional
import yaml

from .models import DetectionCriteria


def load_criteria_from_config(config_path: Path) -> Optional[DetectionCriteria]:
    """Load detection criteria from config file.

    Args:
        config_path: Path to transfer_config.yaml

    Returns:
        DetectionCriteria if file exists, None otherwise
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            return None

        # Extract criteria fields
        from decimal import Decimal

        return DetectionCriteria(
            max_date_difference_days=config_data.get("max_date_difference_days", 2),
            amount_tolerance=Decimal(str(config_data.get("amount_tolerance", "0.00"))),
            max_suspected_date_days=config_data.get("max_suspected_date_days", 4),
            fx_amount_tolerance_percent=Decimal(
                str(config_data.get("fx_amount_tolerance_percent", "5.0"))
            ),
            name_variations=config_data.get("name_variations"),
            fx_enabled_accounts=config_data.get("fx_enabled_accounts"),
        )
    except Exception:
        return None


def save_criteria_to_config(criteria: DetectionCriteria, config_path: Path) -> None:
    """Save detection criteria to config file.

    Args:
        criteria: Detection criteria to save
        config_path: Path to transfer_config.yaml
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_data = {
        "max_date_difference_days": criteria.max_date_difference_days,
        "amount_tolerance": str(criteria.amount_tolerance),
        "max_suspected_date_days": criteria.max_suspected_date_days,
        "fx_amount_tolerance_percent": str(criteria.fx_amount_tolerance_percent),
        "name_variations": criteria.name_variations,
        "fx_enabled_accounts": criteria.fx_enabled_accounts,
    }

    with open(config_path, "w") as f:
        yaml.dump(
            config_data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def get_config_path(ledger_path: Path) -> Path:
    """Get the transfer config path for a ledger.

    Args:
        ledger_path: Path to ledger (file or directory)

    Returns:
        Path to transfer_config.yaml
    """
    if ledger_path.is_file():
        # For single file ledger, put config in same directory
        return ledger_path.parent / "transfer_config.yaml"
    else:
        # For directory ledger, put config in the directory
        return ledger_path / "transfer_config.yaml"
