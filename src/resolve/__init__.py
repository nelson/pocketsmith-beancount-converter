"""Resolve module for handling conflict resolution between transactions."""

from .strategy import (
    ResolutionStrategy,
    NeverChangeStrategy,
    LocalChangesOnlyStrategy,
    RemoteChangesOnlyStrategy,
    RemoteWinsStrategy,
    MergeListsStrategy,
)
from .resolve import ResolutionEngine, resolve_transaction, resolve_field

__all__ = [
    "ResolutionStrategy",
    "NeverChangeStrategy",
    "LocalChangesOnlyStrategy",
    "RemoteChangesOnlyStrategy",
    "RemoteWinsStrategy",
    "MergeListsStrategy",
    "ResolutionEngine",
    "resolve_transaction",
    "resolve_field",
]
