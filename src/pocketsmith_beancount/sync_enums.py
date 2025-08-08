from enum import Enum, auto


class ResolutionStrategy(Enum):
    """Enum for the 5 field resolution strategies."""

    NEVER_CHANGE = 1  # Strategy 1: Warn on conflicts, keep original
    LOCAL_CHANGES_ONLY = 2  # Strategy 2: Write local changes to remote
    REMOTE_CHANGES_ONLY = 3  # Strategy 3: Overwrite local with remote
    REMOTE_WINS = 4  # Strategy 4: Remote takes precedence
    MERGE_LISTS = 5  # Strategy 5: Merge and deduplicate lists


class ChangeType(Enum):
    """Types of changes detected between local and remote."""

    NO_CHANGE = auto()
    LOCAL_ONLY = auto()
    REMOTE_ONLY = auto()
    BOTH_CHANGED = auto()


class SyncStatus(Enum):
    """Status of synchronization operations."""

    SUCCESS = auto()
    CONFLICT = auto()
    ERROR = auto()
    SKIPPED = auto()
    WARNING = auto()


class SyncDirection(Enum):
    """Direction of synchronization."""

    LOCAL_TO_REMOTE = auto()
    REMOTE_TO_LOCAL = auto()
    BIDIRECTIONAL = auto()
    NO_SYNC = auto()
