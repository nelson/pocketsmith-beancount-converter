"""Pattern matching engine for transaction processing rules."""

import re
from typing import Any, Dict, List, Match, Optional, Pattern, Tuple

from .models import TransactionRule


class RuleMatcher:
    """Matches transactions against rule preconditions using regex patterns."""

    def __init__(self) -> None:
        """Initialize the rule matcher."""
        self._compiled_patterns: Dict[int, Dict[str, Pattern[str]]] = {}

    def prepare_rules(self, rules: List[TransactionRule]) -> None:
        """Pre-compile regex patterns for all rules for better performance.

        Args:
            rules: List of transaction rules to prepare
        """
        self._compiled_patterns.clear()

        for rule in rules:
            rule_patterns = {}

            if rule.precondition.account:
                try:
                    rule_patterns["account"] = re.compile(
                        rule.precondition.account, re.IGNORECASE
                    )
                except re.error:
                    # Skip invalid patterns - they should have been caught during loading
                    continue

            if rule.precondition.category:
                try:
                    rule_patterns["category"] = re.compile(
                        rule.precondition.category, re.IGNORECASE
                    )
                except re.error:
                    continue

            if rule.precondition.merchant:
                try:
                    rule_patterns["merchant"] = re.compile(
                        rule.precondition.merchant, re.IGNORECASE
                    )
                except re.error:
                    continue

            if rule.precondition.metadata:
                for meta_key, meta_pattern in rule.precondition.metadata.items():
                    try:
                        rule_patterns[f"metadata.{meta_key}"] = re.compile(
                            meta_pattern, re.IGNORECASE
                        )
                    except re.error:
                        continue

            if rule_patterns:
                self._compiled_patterns[rule.id] = rule_patterns

    def find_matching_rule(
        self, transaction: Dict[str, Any], rules: List[TransactionRule]
    ) -> Optional[Tuple[TransactionRule, Dict[str, Match[str]]]]:
        """Find the first matching rule for a transaction.

        Args:
            transaction: Transaction data from PocketSmith API
            rules: List of rules to match against (should be sorted by priority)

        Returns:
            Tuple of (matching rule, regex match objects) or None if no match
        """
        # Extract transaction fields for matching
        transaction_fields = self._extract_transaction_fields(transaction)

        # Try each rule in priority order (first match wins)
        for rule in rules:
            match_results = self._match_rule(rule, transaction_fields)
            if match_results:
                return rule, match_results

        return None

    def _extract_transaction_fields(
        self, transaction: Dict[str, Any]
    ) -> Dict[str, str]:
        """Extract matchable fields from a transaction.

        Args:
            transaction: Transaction data from PocketSmith API

        Returns:
            Dictionary with account, category, merchant, and metadata fields
        """
        fields = {"account": "", "category": "", "merchant": ""}

        # Extract account information (Assets/Liabilities only)
        if "account" in transaction:
            account_data = transaction["account"]
            if isinstance(account_data, dict):
                account_name = account_data.get("name", "")
                account_type = account_data.get("type", "")

                # Only match against Assets/Liabilities accounts
                if account_type in [
                    "bank",
                    "credit_card",
                    "loan",
                    "investment",
                    "mortgage",
                ]:
                    fields["account"] = account_name

        # Extract category information (Income/Expenses only)
        if "category" in transaction and transaction["category"]:
            category_data = transaction["category"]
            if isinstance(category_data, dict):
                category_title = category_data.get("title", "")
                # PocketSmith categories are typically expense categories
                # We'll match any category that's not a transfer
                if category_title and category_title.lower() != "transfer":
                    fields["category"] = category_title

        # Extract merchant/payee information
        payee = transaction.get("payee", "")
        if payee and isinstance(payee, str):
            fields["merchant"] = payee

        # Extract metadata from transaction notes
        notes = transaction.get("notes", "")
        if notes and isinstance(notes, str):
            metadata = self._parse_metadata_from_notes(notes)
            for key, value in metadata.items():
                fields[f"metadata.{key}"] = value

        return fields

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

    def _match_rule(
        self, rule: TransactionRule, transaction_fields: Dict[str, str]
    ) -> Optional[Dict[str, Match[str]]]:
        """Check if a rule matches against transaction fields.

        Args:
            rule: Rule to test
            transaction_fields: Extracted transaction fields

        Returns:
            Dictionary of field names to regex match objects, or None if no match
        """
        if rule.id not in self._compiled_patterns:
            # Rule patterns not compiled - try to compile on the fly
            self.prepare_rules([rule])
            if rule.id not in self._compiled_patterns:
                return None

        patterns = self._compiled_patterns[rule.id]
        matches = {}

        # All specified conditions must match
        for field_name, pattern in patterns.items():
            transaction_value = transaction_fields.get(field_name, "")

            if not transaction_value:
                # Field is empty/missing - no match possible
                return None

            match = pattern.search(transaction_value)
            if not match:
                # Pattern didn't match - rule fails
                return None

            matches[field_name] = match

        # All conditions matched
        return matches

    def get_match_groups(self, matches: Dict[str, Match[str]]) -> Dict[str, List[str]]:
        """Extract regex groups from match results.

        Args:
            matches: Dictionary of field names to regex match objects

        Returns:
            Dictionary of field names to lists of captured groups
        """
        groups = {}

        for field_name, match in matches.items():
            field_groups = []
            for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                group = match.group(i)
                if group is not None:
                    field_groups.append(group)
            groups[field_name] = field_groups

        return groups

    def substitute_groups_in_text(
        self, text: str, matches: Dict[str, Match[str]]
    ) -> str:
        """Substitute regex groups in transform text.

        Supports patterns like:
        - \\1, \\2 etc. for groups from any field
        - {merchant.1}, {account.2} etc. for groups from specific fields

        Args:
            text: Text containing group references
            matches: Dictionary of field names to regex match objects

        Returns:
            Text with group references substituted
        """

        # First, handle field-specific group references like {merchant.1}
        def substitute_field_groups(match: Match[str]) -> str:
            field_name = match.group(1)
            group_num = int(match.group(2))

            if field_name in matches:
                field_match = matches[field_name]
                if field_match.lastindex and group_num <= field_match.lastindex:
                    group_value = field_match.group(group_num)
                    return group_value if group_value is not None else ""

            return match.group(0)  # Return original if no match

        # Handle {field.N} patterns
        text = re.sub(r"{(\w+)\.(\d+)}", substitute_field_groups, text)

        # Handle simple \\N patterns using the first available match
        def substitute_simple_groups(match: Match[str]) -> str:
            group_num = int(match.group(1))

            # Try each field's matches to find the group
            for field_match in matches.values():
                if field_match.lastindex and group_num <= field_match.lastindex:
                    group_value = field_match.group(group_num)
                    if group_value is not None:
                        return group_value

            return match.group(0)  # Return original if no match

        # Handle \\N patterns
        text = re.sub(r"\\(\d+)", substitute_simple_groups, text)

        return text

    def validate_transaction_for_matching(self, transaction: Dict[str, Any]) -> bool:
        """Check if transaction has minimum required fields for rule matching.

        Args:
            transaction: Transaction data from PocketSmith API

        Returns:
            True if transaction can be matched against rules
        """
        # Must have at least one matchable field
        fields = self._extract_transaction_fields(transaction)
        return any(fields.values())

    def get_matchable_fields_summary(
        self, transaction: Dict[str, Any]
    ) -> Dict[str, str]:
        """Get a summary of fields that can be matched for debugging.

        Args:
            transaction: Transaction data from PocketSmith API

        Returns:
            Dictionary with field names and their values for matching
        """
        return self._extract_transaction_fields(transaction)

    def clear_compiled_patterns(self) -> None:
        """Clear compiled patterns cache."""
        self._compiled_patterns.clear()
