"""YAML rule file loading and validation."""

import re
from pathlib import Path
from typing import Any, List, Set, Union

import yaml

from .models import (
    RuleLoadResult,
    RulePrecondition,
    RuleTransform,
    RuleValidationError,
    TransactionRule,
)


class RuleLoader:
    """Loads and validates transaction processing rules from YAML files."""

    def __init__(self) -> None:
        """Initialize the rule loader."""
        self._loaded_rule_ids: Set[int] = set()

    def load_rules(
        self, path: Union[str, Path], include_disabled: bool = False
    ) -> RuleLoadResult:
        """Load rules from a file or directory.

        Args:
            path: Path to a YAML file or directory containing YAML files
            include_disabled: If True, include disabled rules in the result

        Returns:
            RuleLoadResult with loaded rules and any validation errors
        """
        # Clear loaded rule IDs for this loading session
        self._loaded_rule_ids.clear()

        result = RuleLoadResult()
        path = Path(path)

        if not path.exists():
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="path",
                    error_message=f"Path does not exist: {path}",
                )
            )
            return result

        if path.is_file():
            self._load_file(path, result, include_disabled)
        elif path.is_dir():
            self._load_directory(path, result, include_disabled)
        else:
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="path",
                    error_message=f"Path is not a file or directory: {path}",
                )
            )

        # Sort rules by priority (ID) if loading was successful
        if result.is_successful:
            result.sort_rules_by_priority()

        return result

    def _load_directory(
        self, directory: Path, result: RuleLoadResult, include_disabled: bool = False
    ) -> None:
        """Load all YAML files from a directory."""
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))

        if not yaml_files:
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="directory",
                    error_message=f"No YAML files found in directory: {directory}",
                )
            )
            return

        for yaml_file in sorted(yaml_files):
            self._load_file(yaml_file, result, include_disabled)

    def _load_file(
        self, file_path: Path, result: RuleLoadResult, include_disabled: bool = False
    ) -> None:
        """Load rules from a single YAML file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                result.add_error(
                    RuleValidationError(
                        rule_id=None,
                        field_name="file",
                        error_message=f"File is empty: {file_path}",
                        file_path=str(file_path),
                    )
                )
                return

            try:
                yaml_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                result.add_error(
                    RuleValidationError(
                        rule_id=None,
                        field_name="yaml",
                        error_message=f"YAML parsing error: {e}",
                        file_path=str(file_path),
                    )
                )
                return

            if not isinstance(yaml_data, list):
                result.add_error(
                    RuleValidationError(
                        rule_id=None,
                        field_name="structure",
                        error_message="YAML file must contain a list of rules",
                        file_path=str(file_path),
                    )
                )
                return

            result.files_processed += 1

            for i, rule_data in enumerate(yaml_data, 1):
                self._load_rule(rule_data, result, str(file_path), i, include_disabled)

        except (OSError, IOError) as e:
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="file_access",
                    error_message=f"Cannot read file: {e}",
                    file_path=str(file_path),
                )
            )

    def _load_rule(
        self,
        rule_data: Any,
        result: RuleLoadResult,
        file_path: str,
        line_number: int,
        include_disabled: bool = False,
    ) -> None:
        """Load and validate a single rule from YAML data."""
        if not isinstance(rule_data, dict):
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="rule_structure",
                    error_message="Rule must be a dictionary/mapping",
                    file_path=file_path,
                    line_number=line_number,
                )
            )
            return

        # Validate required top-level keys
        required_keys = {"id", "if", "then"}
        missing_keys = required_keys - set(rule_data.keys())
        if missing_keys:
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="required_keys",
                    error_message=f"Missing required keys: {', '.join(sorted(missing_keys))}",
                    file_path=file_path,
                    line_number=line_number,
                )
            )
            return

        # Validate rule ID
        rule_id_raw = rule_data.get("id")
        if not isinstance(rule_id_raw, int) or rule_id_raw <= 0:
            result.add_error(
                RuleValidationError(
                    rule_id=None,
                    field_name="id",
                    error_message=f"Rule ID must be a positive integer, got: {rule_id_raw}",
                    file_path=file_path,
                    line_number=line_number,
                )
            )
            return

        rule_id = rule_id_raw

        # Check if rule is disabled
        if rule_data.get("disabled", False) and not include_disabled:
            # Skip disabled rules - they are not loaded but don't cause errors unless include_disabled is True
            return

        # Check for duplicate rule IDs
        if rule_id in self._loaded_rule_ids:
            result.add_error(
                RuleValidationError(
                    rule_id=rule_id,
                    field_name="id",
                    error_message=f"Duplicate rule ID: {rule_id}",
                    file_path=file_path,
                    line_number=line_number,
                )
            )
            return

        self._loaded_rule_ids.add(rule_id)

        # Parse preconditions
        precondition_result = self._parse_precondition(
            rule_data["if"], rule_id, file_path, line_number
        )
        if isinstance(precondition_result, RuleValidationError):
            result.add_error(precondition_result)
            return

        precondition = precondition_result

        # Parse transforms
        transform_result = self._parse_transform(
            rule_data["then"], rule_id, file_path, line_number
        )
        if isinstance(transform_result, RuleValidationError):
            result.add_error(transform_result)
            return

        transform = transform_result

        # Create and validate complete rule
        try:
            rule = TransactionRule(
                id=rule_id, precondition=precondition, transform=transform
            )
            result.add_rule(rule)
        except ValueError as e:
            result.add_error(
                RuleValidationError(
                    rule_id=rule_id,
                    field_name="rule_validation",
                    error_message=str(e),
                    file_path=file_path,
                    line_number=line_number,
                )
            )

    def _parse_precondition(
        self, if_data: Any, rule_id: int, file_path: str, line_number: int
    ) -> Union[RulePrecondition, RuleValidationError]:
        """Parse and validate rule preconditions."""
        if not isinstance(if_data, list) or len(if_data) == 0:
            return RuleValidationError(
                rule_id=rule_id,
                field_name="if",
                error_message="'if' must be a non-empty list of conditions",
                file_path=file_path,
                line_number=line_number,
            )

        # Combine all conditions into a single RulePrecondition
        account = None
        category = None
        merchant = None
        metadata = None

        for condition in if_data:
            if not isinstance(condition, dict):
                return RuleValidationError(
                    rule_id=rule_id,
                    field_name="if_condition",
                    error_message="Each condition must be a dictionary",
                    file_path=file_path,
                    line_number=line_number,
                )

            for key, value in condition.items():
                if key not in ["account", "category", "merchant", "metadata"]:
                    return RuleValidationError(
                        rule_id=rule_id,
                        field_name="if_condition",
                        error_message=f"Unknown condition key: {key}. Must be one of: account, category, merchant, metadata",
                        file_path=file_path,
                        line_number=line_number,
                    )

                if key == "metadata":
                    if not isinstance(value, dict):
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Metadata condition must be a dictionary, got: {type(value).__name__}",
                            file_path=file_path,
                            line_number=line_number,
                        )
                    # Validate metadata keys and patterns
                    for meta_key, meta_pattern in value.items():
                        if not isinstance(meta_key, str):
                            return RuleValidationError(
                                rule_id=rule_id,
                                field_name=f"metadata.{meta_key}",
                                error_message=f"Metadata key must be a string, got: {type(meta_key).__name__}",
                                file_path=file_path,
                                line_number=line_number,
                            )
                        if not isinstance(meta_pattern, str):
                            return RuleValidationError(
                                rule_id=rule_id,
                                field_name=f"metadata.{meta_key}",
                                error_message=f"Metadata pattern must be a string, got: {type(meta_pattern).__name__}",
                                file_path=file_path,
                                line_number=line_number,
                            )
                        # Test regex compilation
                        try:
                            re.compile(meta_pattern, re.IGNORECASE)
                        except re.error as e:
                            return RuleValidationError(
                                rule_id=rule_id,
                                field_name=f"metadata.{meta_key}",
                                error_message=f"Invalid regex pattern: {e}",
                                file_path=file_path,
                                line_number=line_number,
                            )
                    metadata = value
                else:
                    if not isinstance(value, str):
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Condition value must be a string, got: {type(value).__name__}",
                            file_path=file_path,
                            line_number=line_number,
                        )

                    # Test regex compilation
                    try:
                        re.compile(value, re.IGNORECASE)
                    except re.error as e:
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Invalid regex pattern: {e}",
                            file_path=file_path,
                            line_number=line_number,
                        )

                    # Assign to precondition fields
                    if key == "account":
                        account = value
                    elif key == "category":
                        category = value
                    elif key == "merchant":
                        merchant = value

        try:
            return RulePrecondition(
                account=account, category=category, merchant=merchant, metadata=metadata
            )
        except ValueError as e:
            return RuleValidationError(
                rule_id=rule_id,
                field_name="precondition",
                error_message=str(e),
                file_path=file_path,
                line_number=line_number,
            )

    def _parse_transform(
        self, then_data: Any, rule_id: int, file_path: str, line_number: int
    ) -> Union[RuleTransform, RuleValidationError]:
        """Parse and validate rule transforms."""
        if not isinstance(then_data, list) or len(then_data) == 0:
            return RuleValidationError(
                rule_id=rule_id,
                field_name="then",
                error_message="'then' must be a non-empty list of transforms",
                file_path=file_path,
                line_number=line_number,
            )

        # Combine all transforms into a single RuleTransform
        category = None
        labels = None
        memo = None
        metadata = None

        for transform in then_data:
            if not isinstance(transform, dict):
                return RuleValidationError(
                    rule_id=rule_id,
                    field_name="then_transform",
                    error_message="Each transform must be a dictionary",
                    file_path=file_path,
                    line_number=line_number,
                )

            for key, value in transform.items():
                if key not in [
                    "category",
                    "labels",
                    "tags",
                    "memo",
                    "narration",
                    "metadata",
                ]:
                    return RuleValidationError(
                        rule_id=rule_id,
                        field_name="then_transform",
                        error_message=f"Unknown transform key: {key}. Must be one of: category, labels, tags, memo, narration, metadata",
                        file_path=file_path,
                        line_number=line_number,
                    )

                # Validate and assign transform values
                if key == "category":
                    if not isinstance(value, str):
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Category must be a string, got: {type(value).__name__}",
                            file_path=file_path,
                            line_number=line_number,
                        )
                    category = value

                elif key in ["labels", "tags"]:
                    # Parse labels/tags - can be string or list
                    parsed_labels = self._parse_labels(
                        value, rule_id, key, file_path, line_number
                    )
                    if isinstance(parsed_labels, RuleValidationError):
                        return parsed_labels
                    labels = parsed_labels

                elif key in ["memo", "narration"]:
                    if not isinstance(value, str):
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Memo/narration must be a string, got: {type(value).__name__}",
                            file_path=file_path,
                            line_number=line_number,
                        )
                    memo = value

                elif key == "metadata":
                    if not isinstance(value, dict):
                        return RuleValidationError(
                            rule_id=rule_id,
                            field_name=key,
                            error_message=f"Metadata must be a dictionary, got: {type(value).__name__}",
                            file_path=file_path,
                            line_number=line_number,
                        )

                    # Validate metadata values
                    for meta_key, meta_value in value.items():
                        if not isinstance(meta_key, str):
                            return RuleValidationError(
                                rule_id=rule_id,
                                field_name=f"metadata.{meta_key}",
                                error_message=f"Metadata key must be a string, got: {type(meta_key).__name__}",
                                file_path=file_path,
                                line_number=line_number,
                            )

                        if not isinstance(meta_value, (str, int, float, bool)):
                            return RuleValidationError(
                                rule_id=rule_id,
                                field_name=f"metadata.{meta_key}",
                                error_message=f"Metadata value must be string, number, or boolean, got: {type(meta_value).__name__}",
                                file_path=file_path,
                                line_number=line_number,
                            )

                    metadata = value

        try:
            return RuleTransform(
                category=category, labels=labels, memo=memo, metadata=metadata
            )
        except ValueError as e:
            return RuleValidationError(
                rule_id=rule_id,
                field_name="transform",
                error_message=str(e),
                file_path=file_path,
                line_number=line_number,
            )

    def _parse_labels(
        self,
        value: Any,
        rule_id: int,
        field_name: str,
        file_path: str,
        line_number: int,
    ) -> Union[List[str], RuleValidationError]:
        """Parse labels/tags value which can be string or list."""
        if isinstance(value, str):
            # Handle comma or space-delimited string
            if "," in value:
                labels = [label.strip() for label in value.split(",")]
            else:
                labels = value.split()
        elif isinstance(value, list):
            labels = []
            for item in value:
                if not isinstance(item, str):
                    return RuleValidationError(
                        rule_id=rule_id,
                        field_name=field_name,
                        error_message=f"All label items must be strings, got: {type(item).__name__}",
                        file_path=file_path,
                        line_number=line_number,
                    )
                labels.append(item)
        else:
            return RuleValidationError(
                rule_id=rule_id,
                field_name=field_name,
                error_message=f"Labels must be a string or list, got: {type(value).__name__}",
                file_path=file_path,
                line_number=line_number,
            )

        # Validate each label
        for label in labels:
            if not label.strip():
                return RuleValidationError(
                    rule_id=rule_id,
                    field_name=field_name,
                    error_message="Empty labels are not allowed",
                    file_path=file_path,
                    line_number=line_number,
                )

        return [label.strip() for label in labels if label.strip()]
