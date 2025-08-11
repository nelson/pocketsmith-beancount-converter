"""Tests for YAML rule loading and validation."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.pocketsmith_beancount.rule_loader import RuleLoader


class TestRuleLoader:
    """Tests for RuleLoader YAML parsing."""

    def test_load_valid_yaml_file(self):
        """Test loading a valid YAML rule file."""
        yaml_content = """
- id: 1
  if:
    - merchant: "McDonalds"
  then:
    - category: "Dining"
    - labels: ["fast-food", "restaurants"]

- id: 2
  if:
    - account: "checking"
    - category: "food"
  then:
    - category: "Groceries"
    - memo: "Grocery shopping"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert result.is_successful
            assert result.rule_count == 2
            assert result.files_processed == 1
            assert len(result.errors) == 0

            # Check first rule
            rule1 = result.rules[0]
            assert rule1.id == 1
            assert rule1.precondition.merchant == "McDonalds"
            assert rule1.precondition.account is None
            assert rule1.transform.category == "Dining"
            assert rule1.transform.get_effective_labels() == [
                "fast-food",
                "restaurants",
            ]

            # Check second rule
            rule2 = result.rules[1]
            assert rule2.id == 2
            assert rule2.precondition.account == "checking"
            assert rule2.precondition.category == "food"
            assert rule2.transform.category == "Groceries"
            assert rule2.transform.get_effective_memo() == "Grocery shopping"

        finally:
            Path(temp_path).unlink()

    def test_load_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Unclosed quote
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert result.rule_count == 0
            assert len(result.errors) > 0
            assert "YAML parsing error" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self):
        """Test handling of nonexistent file."""
        loader = RuleLoader()
        result = loader.load_rules("nonexistent.yaml")

        assert not result.is_successful
        assert len(result.errors) == 1
        assert "Path does not exist" in str(result.errors[0])

    def test_load_empty_file(self):
        """Test handling of empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "File is empty" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_load_directory_with_yaml_files(self):
        """Test loading rules from a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create first YAML file
            (temp_path / "rules1.yaml").write_text("""
- id: 1
  if:
    - merchant: "Test1"
  then:
    - category: "Cat1"
""")

            # Create second YAML file
            (temp_path / "rules2.yaml").write_text("""
- id: 2
  if:
    - merchant: "Test2"  
  then:
    - category: "Cat2"
""")

            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert result.is_successful
            assert result.rule_count == 2
            assert result.files_processed == 2

            # Should be sorted by rule ID
            assert result.rules[0].id == 1
            assert result.rules[1].id == 2

    def test_load_directory_no_yaml_files(self):
        """Test loading from directory with no YAML files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a non-YAML file
            (temp_path / "readme.txt").write_text("Not a YAML file")

            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "No YAML files found" in str(result.errors[0])

    def test_duplicate_rule_ids(self):
        """Test detection of duplicate rule IDs."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test1"
  then:
    - category: "Cat1"
    
- id: 1  # Duplicate ID
  if:
    - merchant: "Test2"
  then:
    - category: "Cat2"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert len(result.errors) == 1
            assert "Duplicate rule ID: 1" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_missing_required_fields(self):
        """Test validation of missing required fields."""
        yaml_content = """
- id: 1
  # Missing 'if' field
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "Missing required keys" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_invalid_rule_id_type(self):
        """Test validation of rule ID type."""
        yaml_content = """
- id: "not_a_number"
  if:
    - merchant: "Test"
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "Rule ID must be a positive integer" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_invalid_precondition_structure(self):
        """Test validation of precondition structure."""
        yaml_content = """
- id: 1
  if: "not_a_list"
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "'if' must be a non-empty list" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_invalid_transform_structure(self):
        """Test validation of transform structure."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then: "not_a_list"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "'then' must be a non-empty list" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_invalid_regex_pattern(self):
        """Test validation of regex patterns."""
        yaml_content = """
- id: 1
  if:
    - merchant: "[invalid regex"
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "Invalid regex pattern" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_unknown_condition_key(self):
        """Test validation of unknown condition keys."""
        yaml_content = """
- id: 1
  if:
    - unknown_field: "test"
  then:
    - category: "Test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "Unknown condition key: unknown_field" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_unknown_transform_key(self):
        """Test validation of unknown transform keys."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then:
    - unknown_field: "test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert not result.is_successful
            assert "Unknown transform key: unknown_field" in str(result.errors[0])

        finally:
            Path(temp_path).unlink()

    def test_labels_parsing_string(self):
        """Test parsing labels as comma-delimited string."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then:
    - labels: "food, dining, restaurant"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert result.is_successful
            rule = result.rules[0]
            assert rule.transform.get_effective_labels() == [
                "food",
                "dining",
                "restaurant",
            ]

        finally:
            Path(temp_path).unlink()

    def test_labels_parsing_list(self):
        """Test parsing labels as YAML list."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then:
    - labels:
      - food
      - dining
      - restaurant
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert result.is_successful
            rule = result.rules[0]
            assert rule.transform.get_effective_labels() == [
                "food",
                "dining",
                "restaurant",
            ]

        finally:
            Path(temp_path).unlink()

    def test_metadata_validation(self):
        """Test metadata field validation."""
        yaml_content = """
- id: 1
  if:
    - merchant: "Test"
  then:
    - metadata:
        string_key: "value"
        int_key: 42
        float_key: 3.14
        bool_key: true
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = RuleLoader()
            result = loader.load_rules(temp_path)

            assert result.is_successful
            rule = result.rules[0]
            metadata = rule.transform.metadata

            assert metadata["string_key"] == "value"
            assert metadata["int_key"] == 42
            assert metadata["float_key"] == 3.14
            assert metadata["bool_key"] is True

        finally:
            Path(temp_path).unlink()

    @patch("pathlib.Path.is_dir", return_value=False)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_file_permission_error(
        self, mock_open, mock_exists, mock_is_file, mock_is_dir
    ):
        """Test handling of file permission errors."""
        loader = RuleLoader()
        result = loader.load_rules("test.yaml")

        assert not result.is_successful
        assert "Cannot read file" in str(result.errors[0])
