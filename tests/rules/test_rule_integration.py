"""Integration tests for rule system end-to-end functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.rules.loader import RuleLoader
from src.rules.matcher import RuleMatcher
from src.rules.transformer import RuleTransformer


class TestRuleIntegration:
    """Integration tests for complete rule workflows."""

    def test_end_to_end_rule_application(self):
        """Test complete rule workflow from YAML to transaction transformation."""
        # Create a sample rule file
        yaml_content = """
- id: 1
  if:
    - merchant: "McDonalds"
  then:
    - category: "Dining"
    - labels: ["fast-food", "restaurants"]
    - memo: "Fast food meal"

- id: 2
  if:
    - account: "credit"
  then:
    - category: "Credit Card"
    - labels: ["+credit", "-cash"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            # Load rules
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            assert result.is_successful
            assert result.rule_count == 2

            # Test transaction matching
            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            # Mock transaction data
            transaction1 = {
                "id": 123,
                "payee": "McDonalds Restaurant #123",
                "category": {"title": "Unknown"},
                "account": {"name": "Checking Account", "type": "bank"},
                "labels": [],
                "memo": "",
            }

            transaction2 = {
                "id": 456,
                "payee": "Some Store",
                "category": {"title": "Shopping"},
                "account": {"name": "Credit Card", "type": "credit_card"},
                "labels": ["shopping"],
                "memo": "Purchase",
            }

            # Test matching
            match1 = matcher.find_matching_rule(transaction1, result.rules)
            assert match1 is not None
            rule1, matches1 = match1
            assert rule1.id == 1

            match2 = matcher.find_matching_rule(transaction2, result.rules)
            assert match2 is not None
            rule2, matches2 = match2
            assert rule2.id == 2

            # Test transformation
            categories = [
                {"id": 100, "title": "Dining"},
                {"id": 200, "title": "Credit Card"},
            ]

            changelog = Mock()
            transformer = RuleTransformer(categories, changelog)

            # Apply first rule
            applications1 = transformer.apply_transform(
                transaction1, rule1.transform, rule1.id, matches1
            )

            assert len(applications1) == 3  # category, labels, memo
            assert all(app.is_successful for app in applications1)
            assert transaction1["category"]["title"] == "Dining"
            assert transaction1["labels"] == ["fast-food", "restaurants"]
            assert transaction1["memo"] == "Fast food meal"

            # Apply second rule
            applications2 = transformer.apply_transform(
                transaction2, rule2.transform, rule2.id, matches2
            )

            assert len(applications2) == 2  # category, labels
            assert all(app.is_successful for app in applications2)
            assert transaction2["category"]["title"] == "Credit Card"
            # Should add credit and remove cash (though cash wasn't there)
            assert "credit" in transaction2["labels"]

        finally:
            Path(rules_file).unlink()

    def test_multiple_rule_priority(self):
        """Test rule priority with multiple matching rules."""
        yaml_content = """
- id: 2
  if:
    - merchant: "Store"
  then:
    - category: "Shopping"
    
- id: 1  # Lower ID = higher priority
  if:
    - merchant: "Store"
  then:
    - category: "Retail"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            assert result.is_successful
            # Rules should be sorted by ID (priority)
            assert result.rules[0].id == 1
            assert result.rules[1].id == 2

            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            transaction = {
                "id": 789,
                "payee": "Some Store",
                "category": {"title": "Unknown"},
                "account": {"name": "Checking", "type": "bank"},
            }

            # Should match the first rule (ID 1, higher priority)
            match = matcher.find_matching_rule(transaction, result.rules)
            assert match is not None
            rule, matches = match
            assert rule.id == 1  # Higher priority rule wins

        finally:
            Path(rules_file).unlink()

    def test_rule_with_regex_groups(self):
        """Test rule with regex group substitution."""
        yaml_content = """
- id: 1
  if:
    - merchant: "STORE (\\\\d+)"
  then:
    - memo: "Visit to store #\\\\1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            assert result.is_successful

            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            transaction = {
                "id": 999,
                "payee": "STORE 1234",
                "category": {"title": "Shopping"},
                "account": {"name": "Checking", "type": "bank"},
                "memo": "",
            }

            match = matcher.find_matching_rule(transaction, result.rules)
            assert match is not None
            rule, matches = match

            # Apply transformation with group substitution
            categories = []
            changelog = Mock()
            transformer = RuleTransformer(categories, changelog)

            applications = transformer.apply_transform(
                transaction, rule.transform, rule.id, matches
            )

            assert len(applications) == 1
            assert applications[0].is_successful
            assert transaction["memo"] == "Visit to store #1234"

        finally:
            Path(rules_file).unlink()

    def test_rule_error_handling(self):
        """Test rule application with errors."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then:
    - category: "NonexistentCategory"  # This will fail
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            assert result.is_successful

            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            transaction = {
                "id": 111,
                "payee": "Test Merchant",
                "category": {"title": "Unknown"},
                "account": {"name": "Checking", "type": "bank"},
            }

            match = matcher.find_matching_rule(transaction, result.rules)
            assert match is not None
            rule, matches = match

            # Apply transformation - should fail due to invalid category
            categories = []  # Empty categories list
            changelog = Mock()
            transformer = RuleTransformer(categories, changelog)

            applications = transformer.apply_transform(
                transaction, rule.transform, rule.id, matches
            )

            assert len(applications) == 1
            # With empty categories list (local beancount mode), category transformation should succeed
            assert not applications[0].has_error
            assert applications[0].status.value == "SUCCESS"

        finally:
            Path(rules_file).unlink()

    def test_rule_metadata_serialization(self):
        """Test metadata serialization to transaction notes."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Business"
  then:
    - metadata:
        expense_type: "business"
        reimbursable: true
        amount: 42.50
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            transaction = {
                "id": 222,
                "payee": "Business Expense",
                "category": {"title": "Unknown"},
                "account": {"name": "Credit", "type": "credit_card"},
                "notes": "",
            }

            match = matcher.find_matching_rule(transaction, result.rules)
            assert match is not None
            rule, matches = match

            categories = []
            changelog = Mock()
            transformer = RuleTransformer(categories, changelog)

            applications = transformer.apply_transform(
                transaction, rule.transform, rule.id, matches
            )

            assert len(applications) == 1
            assert applications[0].is_successful

            # Check metadata serialization
            notes = transaction["notes"]
            assert "amount: 42.5" in notes  # YAML loads as float, loses trailing zero
            assert "expense_type: business" in notes
            assert "reimbursable: True" in notes

        finally:
            Path(rules_file).unlink()

    def test_no_matching_rules(self):
        """Test transaction that matches no rules."""
        yaml_content = """
- id: 1
  if:
    - merchant: "SpecificStore"
  then:
    - category: "Shopping"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            rules_file = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(rules_file)

            matcher = RuleMatcher()
            matcher.prepare_rules(result.rules)

            transaction = {
                "id": 333,
                "payee": "DifferentStore",  # Won't match the rule
                "category": {"title": "Unknown"},
                "account": {"name": "Checking", "type": "bank"},
            }

            match = matcher.find_matching_rule(transaction, result.rules)
            assert match is None  # No rules should match

        finally:
            Path(rules_file).unlink()

    @pytest.mark.skip(reason="Would require actual PocketSmith API key and data")
    def test_rule_with_real_pocketsmith_data(self):
        """Test rules with real PocketSmith transaction data."""
        # This test would require:
        # 1. Valid PocketSmith API key
        # 2. Real transaction data
        # 3. Real category data
        # Skip for now as it requires external dependencies
        pass
