"""Rule transformation engine for applying changes to transactions."""

import re
from decimal import Decimal
from typing import Any, Dict, List, Match, Optional, Union

from .rule_models import RuleApplication, RuleApplicationStatus, RuleTransform


class RuleTransformer:
    """Applies rule transformations to transactions with validation and conflict detection."""

    def __init__(self, categories: List[Dict[str, Any]], changelog: Any) -> None:
        """Initialize the rule transformer.

        Args:
            categories: List of PocketSmith categories for ID resolution
            changelog: Changelog instance for logging transformations
        """
        self.categories = categories
        self.changelog = changelog
        self._category_name_to_id = self._build_category_mapping()

    def _build_category_mapping(self) -> Dict[str, int]:
        """Build a mapping from category names to PocketSmith category IDs."""
        mapping = {}

        for category in self.categories:
            if isinstance(category, dict):
                category_id = category.get("id")
                category_title = category.get("title", "").strip()

                if category_id and category_title:
                    # Case-insensitive mapping
                    mapping[category_title.lower()] = category_id

        return mapping

    def apply_transform(
        self,
        transaction: Dict[str, Any],
        transform: RuleTransform,
        rule_id: int,
        regex_matches: Optional[Dict[str, Match[str]]] = None,
    ) -> List[RuleApplication]:
        """Apply a rule transform to a transaction.

        Args:
            transaction: Transaction data from PocketSmith API
            transform: Rule transform to apply
            rule_id: ID of the rule being applied
            regex_matches: Regex match results for group substitution

        Returns:
            List of RuleApplication results for each field transformation
        """
        applications = []
        transaction_id = str(transaction.get("id", "unknown"))

        # Apply category transform
        if transform.category:
            app = self._apply_category_transform(
                transaction, transform.category, rule_id, transaction_id, regex_matches
            )
            applications.append(app)

        # Apply labels transform
        effective_labels = transform.get_effective_labels()
        if effective_labels:
            app = self._apply_labels_transform(
                transaction, effective_labels, rule_id, transaction_id, regex_matches
            )
            applications.append(app)

        # Apply memo transform
        effective_memo = transform.get_effective_memo()
        if effective_memo:
            app = self._apply_memo_transform(
                transaction, effective_memo, rule_id, transaction_id, regex_matches
            )
            applications.append(app)

        # Apply metadata transform
        if transform.metadata:
            app = self._apply_metadata_transform(
                transaction, transform.metadata, rule_id, transaction_id, regex_matches
            )
            applications.append(app)

        return applications

    def _apply_category_transform(
        self,
        transaction: Dict[str, Any],
        category_name: str,
        rule_id: int,
        transaction_id: str,
        regex_matches: Optional[Dict[str, Match[str]]],
    ) -> RuleApplication:
        """Apply category transformation."""
        # Substitute regex groups if available
        if regex_matches:
            from .rule_matcher import RuleMatcher

            matcher = RuleMatcher()
            category_name = matcher.substitute_groups_in_text(
                category_name, regex_matches
            )

        old_category = (
            transaction.get("category", {}).get("title", "Uncategorized")
            if transaction.get("category")
            else "Uncategorized"
        )

        # Handle special "Uncategorized" case
        if category_name.lower() == "uncategorized":
            # Set category to None/empty
            transaction["category"] = None

            return RuleApplication(
                rule_id=rule_id,
                transaction_id=transaction_id,
                field_name="CATEGORY",
                old_value=old_category,
                new_value="Uncategorized",
                status=RuleApplicationStatus.SUCCESS,
            )

        # Look up category ID
        category_id = self._category_name_to_id.get(category_name.lower())

        if category_id is None:
            return RuleApplication(
                rule_id=rule_id,
                transaction_id=transaction_id,
                field_name="CATEGORY",
                old_value=old_category,
                new_value=category_name,
                status=RuleApplicationStatus.INVALID,
                error_message=f"Category '{category_name}' not found in PocketSmith",
            )

        # Update transaction with new category
        transaction["category"] = {"id": category_id, "title": category_name}

        return RuleApplication(
            rule_id=rule_id,
            transaction_id=transaction_id,
            field_name="CATEGORY",
            old_value=old_category,
            new_value=category_name,
            status=RuleApplicationStatus.SUCCESS,
        )

    def _apply_labels_transform(
        self,
        transaction: Dict[str, Any],
        labels: List[str],
        rule_id: int,
        transaction_id: str,
        regex_matches: Optional[Dict[str, Match[str]]],
    ) -> RuleApplication:
        """Apply labels/tags transformation."""
        # Get current labels
        current_labels = set(transaction.get("labels", []))
        original_labels = current_labels.copy()

        # Process each label operation
        for label in labels:
            # Substitute regex groups if available
            if regex_matches:
                from .rule_matcher import RuleMatcher

                matcher = RuleMatcher()
                label = matcher.substitute_groups_in_text(label, regex_matches)

            # Sanitize label
            sanitized_label = self._sanitize_label(label)

            if not sanitized_label:
                continue

            if sanitized_label.startswith("-"):
                # Remove label
                label_to_remove = sanitized_label[1:]
                current_labels.discard(label_to_remove)
            else:
                # Add label (remove + prefix if present)
                label_to_add = (
                    sanitized_label[1:]
                    if sanitized_label.startswith("+")
                    else sanitized_label
                )
                current_labels.add(label_to_add)

        # Update transaction
        transaction["labels"] = sorted(list(current_labels))

        # Format change description (used in changelog)
        added_labels = current_labels - original_labels
        removed_labels = original_labels - current_labels

        change_parts: List[str] = []
        if added_labels:
            change_parts.extend(f"+{label}" for label in sorted(added_labels))
        if removed_labels:
            change_parts.extend(f"-{label}" for label in sorted(removed_labels))

        return RuleApplication(
            rule_id=rule_id,
            transaction_id=transaction_id,
            field_name="LABELS",
            old_value=sorted(list(original_labels)),
            new_value=sorted(list(current_labels)),
            status=RuleApplicationStatus.SUCCESS,
        )

    def _apply_memo_transform(
        self,
        transaction: Dict[str, Any],
        memo: str,
        rule_id: int,
        transaction_id: str,
        regex_matches: Optional[Dict[str, Match[str]]],
    ) -> RuleApplication:
        """Apply memo/narration transformation."""
        # Substitute regex groups if available
        if regex_matches:
            from .rule_matcher import RuleMatcher

            matcher = RuleMatcher()
            memo = matcher.substitute_groups_in_text(memo, regex_matches)

        old_memo = transaction.get("memo", "")
        warning_message = None

        # Check for existing memo
        if old_memo and old_memo != memo:
            warning_message = f"Overwriting existing memo: '{old_memo}' → '{memo}'"

        # Update transaction
        transaction["memo"] = memo

        return RuleApplication(
            rule_id=rule_id,
            transaction_id=transaction_id,
            field_name="MEMO",
            old_value=old_memo,
            new_value=memo,
            status=RuleApplicationStatus.SUCCESS,
            warning_message=warning_message,
        )

    def _apply_metadata_transform(
        self,
        transaction: Dict[str, Any],
        metadata: Dict[str, Union[str, Decimal, bool, int]],
        rule_id: int,
        transaction_id: str,
        regex_matches: Optional[Dict[str, Match[str]]],
    ) -> RuleApplication:
        """Apply metadata transformation."""
        # Get current metadata (stored in transaction notes)
        current_notes = transaction.get("notes", "")
        current_metadata = self._parse_metadata_from_notes(current_notes)
        original_metadata = current_metadata.copy()

        warnings = []

        # Apply metadata updates
        for key, value in metadata.items():
            # Substitute regex groups in string values
            processed_value: str
            if isinstance(value, str) and regex_matches:
                from .rule_matcher import RuleMatcher

                matcher = RuleMatcher()
                processed_value = matcher.substitute_groups_in_text(
                    value, regex_matches
                )
            else:
                processed_value = str(value)

            # Check for existing key
            if key in current_metadata and current_metadata[key] != processed_value:
                warnings.append(f"{key}: {current_metadata[key]} → {processed_value}")

            current_metadata[key] = processed_value

        # Serialize metadata back to notes
        new_notes = self._serialize_metadata_to_notes(current_metadata)
        transaction["notes"] = new_notes

        warning_message = "; ".join(warnings) if warnings else None

        return RuleApplication(
            rule_id=rule_id,
            transaction_id=transaction_id,
            field_name="METADATA",
            old_value=original_metadata,
            new_value=current_metadata,
            status=RuleApplicationStatus.SUCCESS,
            warning_message=warning_message,
        )

    def _sanitize_label(self, label: str) -> str:
        """Sanitize a label for beancount compatibility.

        Args:
            label: Raw label string

        Returns:
            Sanitized label or empty string if invalid
        """
        if not label or not label.strip():
            return ""

        label = label.strip()

        # Handle +/- prefixes
        prefix = ""
        if label.startswith(("+", "-")):
            prefix = label[0]
            label = label[1:].strip()

        if not label:
            return ""

        # Convert to lowercase
        label = label.lower()

        # Replace spaces, hyphens, underscores with hyphens
        label = re.sub(r"[\s_-]+", "-", label)

        # Remove invalid characters (keep only letters, numbers, hyphens)
        label = re.sub(r"[^a-z0-9-]", "", label)

        # Remove leading/trailing hyphens
        label = label.strip("-")

        if not label:
            return ""

        # Ensure it starts with a letter or number
        if not re.match(r"^[a-z0-9]", label):
            return ""

        return prefix + label

    def _parse_metadata_from_notes(self, notes: str) -> Dict[str, str]:
        """Parse metadata from PocketSmith transaction notes.

        Expected format: "key: value, key2: value2"

        Args:
            notes: Transaction notes string

        Returns:
            Dictionary of metadata key-value pairs
        """
        metadata: Dict[str, str] = {}

        if not notes or not isinstance(notes, str):
            return metadata

        # Split by comma and parse key-value pairs
        pairs = notes.split(",")

        for pair in pairs:
            pair = pair.strip()
            if ":" in pair:
                key, value = pair.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key and value:
                    metadata[key] = value

        return metadata

    def _serialize_metadata_to_notes(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata dictionary to PocketSmith notes format.

        Args:
            metadata: Dictionary of metadata key-value pairs

        Returns:
            Formatted notes string
        """
        if not metadata:
            return ""

        # Sort by key for consistent output
        sorted_items = sorted(metadata.items())

        pairs = []
        for key, value in sorted_items:
            # Convert value to string
            if isinstance(value, bool):
                value_str = "True" if value else "False"
            elif isinstance(value, Decimal):
                value_str = str(value)
            else:
                value_str = str(value)

            pairs.append(f"{key}: {value_str}")

        return ", ".join(pairs)

    def log_applications(self, applications: List[RuleApplication]) -> None:
        """Log rule applications to the changelog.

        Args:
            applications: List of rule applications to log
        """
        for app in applications:
            if app.status == RuleApplicationStatus.SUCCESS:
                if app.has_warning:
                    # Log overwrite warning
                    self.changelog.log_entry(
                        f"MATCH {app.transaction_id} RULE {app.rule_id} OVERWRITE {app.field_name} {app.warning_message}"
                    )
                else:
                    # Log successful change
                    if app.field_name == "LABELS":
                        # Special formatting for labels
                        old_labels = (
                            set(app.old_value)
                            if isinstance(app.old_value, list)
                            else set()
                        )
                        new_labels = (
                            set(app.new_value)
                            if isinstance(app.new_value, list)
                            else set()
                        )
                        added = new_labels - old_labels
                        removed = old_labels - new_labels

                        changes: List[str] = []
                        if added:
                            changes.extend(f"+{label}" for label in sorted(added))
                        if removed:
                            changes.extend(f"-{label}" for label in sorted(removed))

                        change_desc = " ".join(changes) if changes else "no changes"
                        self.changelog.log_entry(
                            f"MATCH {app.transaction_id} RULE {app.rule_id} {app.field_name} {change_desc}"
                        )
                    else:
                        self.changelog.log_entry(
                            f"MATCH {app.transaction_id} RULE {app.rule_id} {app.field_name} {app.new_value}"
                        )

            elif app.status == RuleApplicationStatus.INVALID:
                # Log invalid transform
                self.changelog.log_entry(
                    f"MATCH {app.transaction_id} RULE {app.rule_id} INVALID {app.field_name} {app.new_value}"
                )

            elif app.status == RuleApplicationStatus.ERROR:
                # Log error
                error_msg = app.error_message or "Unknown error"
                self.changelog.log_entry(
                    f"MATCH {app.transaction_id} RULE {app.rule_id} ERROR {app.field_name} {error_msg}"
                )
