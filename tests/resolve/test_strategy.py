"""Tests for resolve.strategy module functionality."""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st

from src.resolve.strategy import (
    ResolutionStrategy,
    NeverChangeStrategy,
    LocalChangesOnlyStrategy,
    RemoteChangesOnlyStrategy,
    RemoteWinsStrategy,
    MergeListsStrategy,
    ResolutionStrategyType,
)


class TestResolutionStrategyType:
    """Test ResolutionStrategyType enum."""

    def test_strategy_type_values(self):
        """Test strategy type enum values."""
        assert ResolutionStrategyType.NEVER_CHANGE.value == "never_change"
        assert ResolutionStrategyType.LOCAL_CHANGES_ONLY.value == "local_changes_only"
        assert ResolutionStrategyType.REMOTE_CHANGES_ONLY.value == "remote_changes_only"
        assert ResolutionStrategyType.REMOTE_WINS.value == "remote_wins"
        assert ResolutionStrategyType.MERGE_LISTS.value == "merge_lists"


class TestResolutionStrategy:
    """Test abstract ResolutionStrategy base class."""

    def test_resolution_strategy_is_abstract(self):
        """Test that ResolutionStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ResolutionStrategy()

    def test_resolution_strategy_subclass_must_implement_resolve(self):
        """Test that subclasses must implement resolve method."""

        class IncompleteStrategy(ResolutionStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()


class TestNeverChangeStrategy:
    """Test NeverChangeStrategy implementation."""

    def test_never_change_strategy_creation(self):
        """Test creating NeverChangeStrategy."""
        strategy = NeverChangeStrategy()
        assert strategy.strategy_type == ResolutionStrategyType.NEVER_CHANGE

    def test_never_change_resolve_returns_remote(self):
        """Test that never change strategy always returns remote value."""
        strategy = NeverChangeStrategy()

        result = strategy.resolve("test_field", "local_value", "remote_value")
        assert result == "remote_value"  # Always uses remote as authoritative

    def test_never_change_resolve_with_none_local(self):
        """Test never change strategy with None local value."""
        strategy = NeverChangeStrategy()

        result = strategy.resolve("test_field", None, "remote_value")
        assert result == "remote_value"  # Always returns remote value

    def test_never_change_resolve_with_various_types(self):
        """Test never change strategy with various value types."""
        strategy = NeverChangeStrategy()

        # String values
        assert strategy.resolve("field", "local", "remote") == "remote"

        # Integer values
        assert strategy.resolve("field", 100, 200) == 200

        # List values
        assert strategy.resolve("field", [1, 2], [3, 4]) == [3, 4]

        # Dict values
        local_dict = {"key": "local"}
        remote_dict = {"key": "remote"}
        assert strategy.resolve("field", local_dict, remote_dict) == remote_dict

    def test_never_change_should_write_back(self):
        """Test never change strategy write-back requirements."""
        strategy = NeverChangeStrategy()

        # Should never write back for immutable fields
        assert not strategy.should_write_back("field", "resolved", "original_remote")
        assert not strategy.should_write_back("field", "same", "same")
        assert not strategy.should_write_back("field", "different", "original")


class TestLocalChangesOnlyStrategy:
    """Test LocalChangesOnlyStrategy implementation."""

    def test_local_changes_only_creation(self):
        """Test creating LocalChangesOnlyStrategy."""
        strategy = LocalChangesOnlyStrategy()
        assert strategy.strategy_type == ResolutionStrategyType.LOCAL_CHANGES_ONLY

    def test_local_changes_only_with_newer_local(self):
        """Test local changes only with newer local timestamp."""
        strategy = LocalChangesOnlyStrategy()

        # Mock transactions with timestamps
        local_transaction = {"last_modified": "2024-01-15T12:00:00Z"}
        remote_transaction = {"last_modified": "2024-01-15T10:00:00Z"}

        result = strategy.resolve(
            "test_field",
            "local_value",
            "remote_value",
            local_transaction,
            remote_transaction,
        )

        assert result == "local_value"

    def test_local_changes_only_with_older_local(self):
        """Test local changes only always uses local value."""
        strategy = LocalChangesOnlyStrategy()

        # LocalChangesOnlyStrategy always uses local value regardless of timestamps
        result = strategy.resolve("test_field", "local_value", "remote_value")

        assert result == "local_value"  # Always returns local value

    def test_local_changes_only_missing_timestamps(self):
        """Test local changes only with missing timestamps."""
        strategy = LocalChangesOnlyStrategy()

        # Without timestamps, should default to local
        result = strategy.resolve("test_field", "local_value", "remote_value")
        assert result == "local_value"

        # With one missing timestamp
        local_transaction = {"last_modified": "2024-01-15T12:00:00Z"}
        result = strategy.resolve(
            "test_field", "local_value", "remote_value", local_transaction, None
        )
        assert result == "local_value"

    def test_local_changes_only_should_write_back(self):
        """Test write-back requirements for local changes only."""
        strategy = LocalChangesOnlyStrategy()

        # Should not write back if resolved value equals original remote
        assert not strategy.should_write_back("field", "same", "same")

        # Should write back if resolved (local) value differs from original remote
        assert strategy.should_write_back("field", "local_value", "remote_value")


class TestRemoteChangesOnlyStrategy:
    """Test RemoteChangesOnlyStrategy implementation."""

    def test_remote_changes_only_creation(self):
        """Test creating RemoteChangesOnlyStrategy."""
        strategy = RemoteChangesOnlyStrategy()
        assert strategy.strategy_type == ResolutionStrategyType.REMOTE_CHANGES_ONLY

    def test_remote_changes_only_with_newer_remote(self):
        """Test remote changes only with newer remote timestamp."""
        strategy = RemoteChangesOnlyStrategy()

        local_transaction = {"last_modified": "2024-01-15T10:00:00Z"}
        remote_transaction = {"last_modified": "2024-01-15T12:00:00Z"}

        result = strategy.resolve(
            "test_field",
            "local_value",
            "remote_value",
            local_transaction,
            remote_transaction,
        )

        assert result == "remote_value"

    def test_remote_changes_only_always_uses_remote(self):
        """Test remote changes only always uses remote value."""
        strategy = RemoteChangesOnlyStrategy()

        # RemoteChangesOnlyStrategy always uses remote value
        result = strategy.resolve("test_field", "local_value", "remote_value")

        assert result == "remote_value"  # Always returns remote value


class TestRemoteWinsStrategy:
    """Test RemoteWinsStrategy implementation."""

    def test_remote_wins_creation(self):
        """Test creating RemoteWinsStrategy."""
        strategy = RemoteWinsStrategy()
        assert strategy.strategy_type == ResolutionStrategyType.REMOTE_WINS

    def test_remote_wins_always_returns_remote(self):
        """Test that remote wins strategy always returns remote value."""
        strategy = RemoteWinsStrategy()

        result = strategy.resolve("test_field", "local_value", "remote_value")
        assert result == "remote_value"

    def test_remote_wins_with_none_remote(self):
        """Test remote wins strategy with None remote value."""
        strategy = RemoteWinsStrategy()

        result = strategy.resolve("test_field", "local_value", None)
        assert result is None

    def test_remote_wins_should_write_back(self):
        """Test remote wins strategy write-back requirements."""
        strategy = RemoteWinsStrategy()

        # Should never write back since remote always wins
        assert not strategy.should_write_back("field", "remote_value", "remote_value")
        assert not strategy.should_write_back("field", "different", "original")


class TestMergeListsStrategy:
    """Test MergeListsStrategy implementation."""

    def test_merge_lists_creation(self):
        """Test creating MergeListsStrategy."""
        strategy = MergeListsStrategy()
        assert strategy.strategy_type == ResolutionStrategyType.MERGE_LISTS

    def test_merge_lists_basic_merge(self):
        """Test basic list merging."""
        strategy = MergeListsStrategy()

        local_list = ["a", "b", "c"]
        remote_list = ["c", "d", "e"]

        result = strategy.resolve("labels", local_list, remote_list)

        # Should contain all unique items
        assert set(result) == {"a", "b", "c", "d", "e"}
        # Should preserve order (local items first)
        assert result[:3] == ["a", "b", "c"]
        assert "d" in result
        assert "e" in result

    def test_merge_lists_empty_lists(self):
        """Test merging with empty lists."""
        strategy = MergeListsStrategy()

        # Empty local list
        result = strategy.resolve("labels", [], ["a", "b"])
        assert result == ["a", "b"]

        # Empty remote list
        result = strategy.resolve("labels", ["a", "b"], [])
        assert result == ["a", "b"]

        # Both empty
        result = strategy.resolve("labels", [], [])
        assert result == []

    def test_merge_lists_none_values(self):
        """Test merging with None values."""
        strategy = MergeListsStrategy()

        # None local
        result = strategy.resolve("labels", None, ["a", "b"])
        assert result == ["a", "b"]

        # None remote
        result = strategy.resolve("labels", ["a", "b"], None)
        assert result == ["a", "b"]

        # Both None
        result = strategy.resolve("labels", None, None)
        assert result == []

    def test_merge_lists_duplicate_removal(self):
        """Test that duplicates are removed during merge."""
        strategy = MergeListsStrategy()

        local_list = ["a", "b", "c", "a"]  # Has duplicate
        remote_list = ["b", "d", "e", "b"]  # Has duplicate

        result = strategy.resolve("labels", local_list, remote_list)

        # Should have no duplicates
        assert len(result) == len(set(result))
        # Should contain all unique items
        assert set(result) == {"a", "b", "c", "d", "e"}

    def test_merge_lists_non_list_values(self):
        """Test merge strategy with non-list values."""
        strategy = MergeListsStrategy()

        # String values - should convert to lists
        result = strategy.resolve("field", "local", "remote")
        assert isinstance(result, list)

        # Mixed types
        result = strategy.resolve("field", ["a", "b"], "c")
        assert isinstance(result, list)
        assert "c" in result

    def test_merge_lists_should_write_back(self):
        """Test merge lists strategy write-back requirements."""
        strategy = MergeListsStrategy()

        # Should write back if merged result differs from original remote
        merged_result = ["a", "b", "c", "d"]
        original_remote = ["c", "d"]
        assert strategy.should_write_back("labels", merged_result, original_remote)

        # Should not write back if merged result equals original remote
        same_list = ["a", "b"]
        assert not strategy.should_write_back("labels", same_list, same_list)


class TestPropertyBasedTests:
    """Property-based tests for strategy functionality."""

    @given(st.text(min_size=0, max_size=100))
    def test_never_change_strategy_properties(self, value):
        """Property test: never change should always return remote value."""
        strategy = NeverChangeStrategy()

        remote_value = "different_value"
        result = strategy.resolve("field", value, remote_value)
        assert result == remote_value  # Always returns remote

    @given(st.text(min_size=0, max_size=100))
    def test_remote_wins_strategy_properties(self, value):
        """Property test: remote wins should always return remote value."""
        strategy = RemoteWinsStrategy()

        result = strategy.resolve("field", "local_value", value)
        assert result == value

    @given(st.lists(st.text(min_size=0, max_size=20), min_size=0, max_size=10))
    def test_merge_lists_strategy_properties(self, local_list):
        """Property test: merge strategy should preserve all unique items."""
        strategy = MergeListsStrategy()
        remote_list = ["additional", "items"]

        result = strategy.resolve("labels", local_list, remote_list)

        # Should be a list
        assert isinstance(result, list)

        # Should contain all items from both lists
        all_items = set(local_list + remote_list)
        result_items = set(result)
        assert result_items >= all_items

        # Should not have duplicates
        assert len(result) == len(set(result))

    @given(
        st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))
    )
    def test_timestamp_based_strategies_properties(self, timestamp):
        """Property test: timestamp-based strategies should handle various timestamps."""
        local_strategy = LocalChangesOnlyStrategy()
        remote_strategy = RemoteChangesOnlyStrategy()

        timestamp_str = timestamp.isoformat() + "Z"
        older_timestamp = "2019-01-01T00:00:00Z"
        newer_timestamp = "2031-01-01T00:00:00Z"

        local_transaction = {"last_modified": timestamp_str}
        older_remote = {"last_modified": older_timestamp}
        newer_remote = {"last_modified": newer_timestamp}

        # Local changes only should prefer local when local is newer
        result = local_strategy.resolve(
            "field", "local", "remote", local_transaction, older_remote
        )
        assert result == "local"

        # Remote changes only should prefer remote when remote is newer
        result = remote_strategy.resolve(
            "field", "local", "remote", local_transaction, newer_remote
        )
        assert result == "remote"

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=20))
    def test_merge_strategy_order_preservation(self, items):
        """Property test: merge strategy should preserve order correctly."""
        strategy = MergeListsStrategy()

        # Split items into local and remote
        mid = len(items) // 2
        local_items = items[:mid]
        remote_items = items[mid:]

        result = strategy.resolve("field", local_items, remote_items)

        # Local items should appear before remote items (when unique)
        if local_items and remote_items:
            # Find first occurrence of local and remote items
            local_positions = [
                result.index(item) for item in local_items if item in result
            ]
            remote_positions = [
                result.index(item)
                for item in remote_items
                if item in result and item not in local_items
            ]

            if local_positions and remote_positions:
                assert min(local_positions) < min(remote_positions)

    @given(st.one_of(st.text(), st.integers(), st.lists(st.text()), st.none()))
    def test_strategy_write_back_consistency(self, value):
        """Property test: write-back should be consistent across strategies."""
        strategies = [
            NeverChangeStrategy(),
            RemoteWinsStrategy(),
            LocalChangesOnlyStrategy(),
            RemoteChangesOnlyStrategy(),
            MergeListsStrategy(),
        ]

        for strategy in strategies:
            # Test should_write_back method exists and returns boolean
            different_value = "different" if value != "different" else "other"
            should_wb = strategy.should_write_back("field", value, different_value)
            assert isinstance(should_wb, bool)
