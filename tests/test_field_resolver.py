"""Tests for field resolution strategies."""

import pytest
from unittest.mock import Mock

from src.pocketsmith_beancount.field_resolver import (
    Strategy1NeverChange,
    Strategy2LocalChangesOnly,
    Strategy3RemoteChangesOnly,
    Strategy4RemoteWins,
    Strategy5MergeLists,
    FieldResolverFactory,
)
from src.pocketsmith_beancount.field_mapping import FieldMapping
from src.pocketsmith_beancount.sync_models import SyncTransaction
from src.pocketsmith_beancount.sync_enums import ResolutionStrategy
from src.pocketsmith_beancount.sync_exceptions import FieldResolutionError


class TestStrategy1NeverChange:
    """Test Strategy 1: Never Change fields."""

    def test_strategy_property(self):
        """Test strategy property returns correct value."""
        resolver = Strategy1NeverChange()
        assert resolver.strategy == ResolutionStrategy.NEVER_CHANGE

    def test_resolve_no_conflict(self):
        """Test resolution when values are the same."""
        resolver = Strategy1NeverChange()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "amount", 100.0, 100.0)
        assert result == 100.0

    def test_resolve_with_conflict(self, caplog):
        """Test resolution when values differ - should warn and use remote."""
        import logging

        caplog.set_level(logging.WARNING)

        resolver = Strategy1NeverChange()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "amount", 100.0, 150.0)
        assert result == 150.0  # Should use remote value
        assert "Unexpected change detected in immutable field" in caplog.text
        assert "transaction 123" in caplog.text

    def test_should_write_back(self):
        """Test that never change fields never write back."""
        resolver = Strategy1NeverChange()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(transaction, "amount", 100.0, 150.0)
        assert result is False


class TestStrategy2LocalChangesOnly:
    """Test Strategy 2: Local Changes Only fields."""

    def test_strategy_property(self):
        """Test strategy property returns correct value."""
        resolver = Strategy2LocalChangesOnly()
        assert resolver.strategy == ResolutionStrategy.LOCAL_CHANGES_ONLY

    def test_resolve_no_change(self):
        """Test resolution when values are the same."""
        resolver = Strategy2LocalChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "note", "same note", "same note")
        assert result == "same note"

    def test_resolve_with_local_change(self, caplog):
        """Test resolution when local value differs."""
        import logging

        caplog.set_level(logging.INFO)

        resolver = Strategy2LocalChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "note", "local note", "remote note")
        assert result == "local note"  # Should use local value
        assert "Local change detected" in caplog.text
        assert "Will write back to remote" in caplog.text

    def test_should_write_back_when_different(self):
        """Test write-back when values differ."""
        resolver = Strategy2LocalChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "note", "local note", "remote note"
        )
        assert result is True

    def test_should_write_back_when_same(self):
        """Test no write-back when values are the same."""
        resolver = Strategy2LocalChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "note", "same note", "same note"
        )
        assert result is False


class TestStrategy3RemoteChangesOnly:
    """Test Strategy 3: Remote Changes Only fields."""

    def test_strategy_property(self):
        """Test strategy property returns correct value."""
        resolver = Strategy3RemoteChangesOnly()
        assert resolver.strategy == ResolutionStrategy.REMOTE_CHANGES_ONLY

    def test_resolve_no_change(self):
        """Test resolution when values are the same."""
        resolver = Strategy3RemoteChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "updated_at", "2024-01-15", "2024-01-15")
        assert result == "2024-01-15"

    def test_resolve_with_remote_change(self, caplog):
        """Test resolution when remote value differs."""
        import logging

        caplog.set_level(logging.INFO)

        resolver = Strategy3RemoteChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "updated_at", "2024-01-15", "2024-01-16")
        assert result == "2024-01-16"  # Should use remote value
        assert "Remote change detected" in caplog.text
        assert "Updating local value" in caplog.text

    def test_should_write_back(self):
        """Test that remote-only fields never write back."""
        resolver = Strategy3RemoteChangesOnly()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "updated_at", "2024-01-16", "2024-01-15"
        )
        assert result is False


class TestStrategy4RemoteWins:
    """Test Strategy 4: Remote Wins fields."""

    def test_strategy_property(self):
        """Test strategy property returns correct value."""
        resolver = Strategy4RemoteWins()
        assert resolver.strategy == ResolutionStrategy.REMOTE_WINS

    def test_resolve_no_conflict(self):
        """Test resolution when values are the same."""
        resolver = Strategy4RemoteWins()
        transaction = SyncTransaction(id="123")

        category = {"id": 1, "title": "Food"}
        result = resolver.resolve(transaction, "category", category, category)
        assert result == category

    def test_resolve_with_conflict(self, caplog):
        """Test resolution when values differ - should use remote."""
        import logging

        caplog.set_level(logging.INFO)

        resolver = Strategy4RemoteWins()
        transaction = SyncTransaction(id="123")

        local_category = {"id": 1, "title": "Food"}
        remote_category = {"id": 2, "title": "Transport"}

        result = resolver.resolve(
            transaction, "category", local_category, remote_category
        )
        assert result == remote_category  # Should use remote value
        assert "Conflict in field 'category'" in caplog.text
        assert "Using remote value" in caplog.text

    def test_should_write_back(self):
        """Test that remote wins fields never write back."""
        resolver = Strategy4RemoteWins()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "category", {"id": 2}, {"id": 1}
        )
        assert result is False


class TestStrategy5MergeLists:
    """Test Strategy 5: Merge Lists fields."""

    def test_strategy_property(self):
        """Test strategy property returns correct value."""
        resolver = Strategy5MergeLists()
        assert resolver.strategy == ResolutionStrategy.MERGE_LISTS

    def test_resolve_empty_lists(self):
        """Test merging empty lists."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "labels", [], [])
        assert result == []

    def test_resolve_one_empty_list(self):
        """Test merging when one list is empty."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "labels", ["tag1", "tag2"], [])
        assert result == ["tag1", "tag2"]

        result = resolver.resolve(transaction, "labels", [], ["tag3", "tag4"])
        assert result == ["tag3", "tag4"]

    def test_resolve_merge_unique_lists(self, caplog):
        """Test merging lists with unique items."""
        import logging

        caplog.set_level(logging.INFO)

        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(
            transaction, "labels", ["tag1", "tag2"], ["tag3", "tag4"]
        )
        assert result == ["tag1", "tag2", "tag3", "tag4"]
        assert "Merged list field 'labels'" in caplog.text

    def test_resolve_merge_overlapping_lists(self):
        """Test merging lists with overlapping items."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(
            transaction, "labels", ["tag1", "tag2"], ["tag2", "tag3"]
        )
        assert result == ["tag1", "tag2", "tag3"]  # Deduplicated

    def test_resolve_preserve_order(self):
        """Test that merging preserves order (local first)."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.resolve(transaction, "labels", ["b", "a"], ["c", "a"])
        assert result == ["b", "a", "c"]  # Local order preserved, remote items added

    def test_ensure_list_with_none(self):
        """Test _ensure_list with None value."""
        resolver = Strategy5MergeLists()
        assert resolver._ensure_list(None) == []

    def test_ensure_list_with_list(self):
        """Test _ensure_list with list value."""
        resolver = Strategy5MergeLists()
        test_list = ["a", "b", "c"]
        assert resolver._ensure_list(test_list) == test_list

    def test_ensure_list_with_tuple(self):
        """Test _ensure_list with tuple value."""
        resolver = Strategy5MergeLists()
        assert resolver._ensure_list(("a", "b", "c")) == ["a", "b", "c"]

    def test_ensure_list_with_set(self):
        """Test _ensure_list with set value."""
        resolver = Strategy5MergeLists()
        result = resolver._ensure_list({"a", "b", "c"})
        assert set(result) == {"a", "b", "c"}  # Order may vary for sets

    def test_ensure_list_with_single_value(self):
        """Test _ensure_list with single value."""
        resolver = Strategy5MergeLists()
        assert resolver._ensure_list("single") == ["single"]

    def test_should_write_back_when_different(self):
        """Test write-back when merged list differs from remote."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "labels", ["tag1", "tag2", "tag3"], ["tag1", "tag2"]
        )
        assert result is True

    def test_should_write_back_when_same(self):
        """Test no write-back when merged list same as remote."""
        resolver = Strategy5MergeLists()
        transaction = SyncTransaction(id="123")

        result = resolver.should_write_back(
            transaction, "labels", ["tag1", "tag2"], ["tag1", "tag2"]
        )
        assert result is False


class TestFieldResolverFactory:
    """Test FieldResolverFactory."""

    def test_get_resolver_strategy1(self):
        """Test getting Strategy 1 resolver."""
        resolver = FieldResolverFactory.get_resolver(ResolutionStrategy.NEVER_CHANGE)
        assert isinstance(resolver, Strategy1NeverChange)

    def test_get_resolver_strategy2(self):
        """Test getting Strategy 2 resolver."""
        resolver = FieldResolverFactory.get_resolver(
            ResolutionStrategy.LOCAL_CHANGES_ONLY
        )
        assert isinstance(resolver, Strategy2LocalChangesOnly)

    def test_get_resolver_strategy3(self):
        """Test getting Strategy 3 resolver."""
        resolver = FieldResolverFactory.get_resolver(
            ResolutionStrategy.REMOTE_CHANGES_ONLY
        )
        assert isinstance(resolver, Strategy3RemoteChangesOnly)

    def test_get_resolver_strategy4(self):
        """Test getting Strategy 4 resolver."""
        resolver = FieldResolverFactory.get_resolver(ResolutionStrategy.REMOTE_WINS)
        assert isinstance(resolver, Strategy4RemoteWins)

    def test_get_resolver_strategy5(self):
        """Test getting Strategy 5 resolver."""
        resolver = FieldResolverFactory.get_resolver(ResolutionStrategy.MERGE_LISTS)
        assert isinstance(resolver, Strategy5MergeLists)

    def test_get_resolver_invalid_strategy(self):
        """Test getting resolver for invalid strategy."""
        with pytest.raises(
            FieldResolutionError, match="Unsupported resolution strategy"
        ):
            # Create a mock strategy that doesn't exist
            invalid_strategy = Mock()
            invalid_strategy.__str__ = Mock(return_value="INVALID_STRATEGY")
            FieldResolverFactory.get_resolver(invalid_strategy)

    def test_get_all_strategies(self):
        """Test getting all supported strategies."""
        strategies = FieldResolverFactory.get_all_strategies()
        expected = {
            ResolutionStrategy.NEVER_CHANGE,
            ResolutionStrategy.LOCAL_CHANGES_ONLY,
            ResolutionStrategy.REMOTE_CHANGES_ONLY,
            ResolutionStrategy.REMOTE_WINS,
            ResolutionStrategy.MERGE_LISTS,
        }
        assert strategies == expected


class TestFieldMapping:
    """Test FieldMapping configuration."""

    def test_get_strategy_valid_field(self):
        """Test getting strategy for valid field."""
        assert FieldMapping.get_strategy("amount") == ResolutionStrategy.NEVER_CHANGE
        assert (
            FieldMapping.get_strategy("note") == ResolutionStrategy.LOCAL_CHANGES_ONLY
        )
        assert (
            FieldMapping.get_strategy("updated_at")
            == ResolutionStrategy.REMOTE_CHANGES_ONLY
        )
        assert FieldMapping.get_strategy("category") == ResolutionStrategy.REMOTE_WINS
        assert FieldMapping.get_strategy("labels") == ResolutionStrategy.MERGE_LISTS

    def test_get_strategy_invalid_field(self):
        """Test getting strategy for invalid field."""
        with pytest.raises(
            ValueError, match="No resolution strategy defined for field"
        ):
            FieldMapping.get_strategy("invalid_field")

    def test_is_immutable(self):
        """Test immutable field detection."""
        assert FieldMapping.is_immutable("amount") is True
        assert FieldMapping.is_immutable("id") is True
        assert FieldMapping.is_immutable("note") is False

    def test_is_writable(self):
        """Test writable field detection."""
        assert FieldMapping.is_writable("note") is True
        assert FieldMapping.is_writable("labels") is True
        assert FieldMapping.is_writable("amount") is False

    def test_is_list_field(self):
        """Test list field detection."""
        assert FieldMapping.is_list_field("labels") is True
        assert FieldMapping.is_list_field("tags") is True
        assert FieldMapping.is_list_field("note") is False

    def test_is_timestamp_field(self):
        """Test timestamp field detection."""
        assert FieldMapping.is_timestamp_field("updated_at") is True
        assert FieldMapping.is_timestamp_field("created_at") is True
        assert FieldMapping.is_timestamp_field("note") is False

    def test_get_all_fields(self):
        """Test getting all mapped fields."""
        fields = FieldMapping.get_all_fields()
        assert "amount" in fields
        assert "note" in fields
        assert "labels" in fields
        assert len(fields) > 0

    def test_get_fields_by_strategy(self):
        """Test getting fields by strategy."""
        never_change_fields = FieldMapping.get_fields_by_strategy(
            ResolutionStrategy.NEVER_CHANGE
        )
        assert "amount" in never_change_fields
        assert "id" in never_change_fields

        local_only_fields = FieldMapping.get_fields_by_strategy(
            ResolutionStrategy.LOCAL_CHANGES_ONLY
        )
        assert "note" in local_only_fields
        assert "memo" in local_only_fields

    def test_validate_field_coverage(self):
        """Test field coverage validation."""
        # Test with all mapped fields
        mapped_fields = {"amount", "note", "labels"}
        unmapped = FieldMapping.validate_field_coverage(mapped_fields)
        assert len(unmapped) == 0

        # Test with unmapped fields
        mixed_fields = {"amount", "note", "unknown_field", "another_unknown"}
        unmapped = FieldMapping.validate_field_coverage(mixed_fields)
        assert "unknown_field" in unmapped
        assert "another_unknown" in unmapped
        assert "amount" not in unmapped
        assert "note" not in unmapped
