"""Encode/decode metadata in PocketSmith note field.

Uses pattern: [key:value] for all metadata fields.
Examples:
  - [paired:12345]
  - [reconciled:true]
  - Multiple: "My note [paired:12345] [reconciled:true]"
"""

import re
from typing import Dict, Any, Tuple, Optional


def encode_metadata_in_note(note: Optional[str], metadata: Dict[str, Any]) -> str:
    """Add metadata tags to note field.

    Args:
        note: Existing note text (may contain existing metadata)
        metadata: Dict of metadata to encode

    Returns:
        Note with metadata encoded as [key:value] tags

    Example:
        >>> encode_metadata_in_note("My note", {"paired": 12345})
        "My note [paired:12345]"
        >>> encode_metadata_in_note("Note [paired:111]", {"paired": 222})
        "Note [paired:222]"
    """
    # Start with clean note (remove existing metadata)
    clean_note, _ = decode_metadata_from_note(note or "")

    # Append new metadata
    metadata_tags = []
    for key, value in metadata.items():
        # Skip None values
        if value is None:
            continue
        metadata_tags.append(f"[{key}:{value}]")

    if metadata_tags:
        result = f"{clean_note} {' '.join(metadata_tags)}".strip()
    else:
        result = clean_note

    return result


def decode_metadata_from_note(note: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Extract metadata from note, return (clean_note, metadata_dict).

    Args:
        note: Note text with potential [key:value] tags

    Returns:
        Tuple of (note_without_metadata, metadata_dict)

    Example:
        >>> decode_metadata_from_note("My note [paired:12345]")
        ("My note", {"paired": 12345})
    """
    if not note:
        return "", {}

    metadata: Dict[str, Any] = {}

    # Find all [key:value] patterns
    pattern = r"\[(\w+):([^\]]+)\]"
    matches = re.finditer(pattern, note)

    for match in matches:
        key, value = match.group(1), match.group(2)

        # Type conversion for known fields
        if key == "paired":
            try:
                metadata[key] = int(value)
            except ValueError:
                metadata[key] = value  # Keep as string if can't convert
        elif key in ["reconciled", "reviewed"]:
            metadata[key] = value.lower() in ["true", "1", "yes"]
        elif key == "suspect_reason":
            # Keep as string
            metadata[key] = value
        else:
            metadata[key] = value

    # Remove metadata tags from note
    clean_note = re.sub(pattern, "", note).strip()
    # Clean up multiple consecutive spaces without touching newlines/carriage returns
    clean_note = re.sub(r" {2,}", " ", clean_note)

    return clean_note, metadata


def remove_metadata_from_note(note: Optional[str]) -> str:
    """Remove all metadata tags from note.

    Args:
        note: Note with potential metadata

    Returns:
        Clean note text

    Example:
        >>> remove_metadata_from_note("Note [paired:123] [other:val]")
        "Note"
    """
    clean_note, _ = decode_metadata_from_note(note)
    return clean_note


def update_metadata_in_note(
    note: Optional[str], updates: Dict[str, Any], remove_keys: Optional[set] = None
) -> str:
    """Update specific metadata fields in note.

    Args:
        note: Existing note
        updates: Metadata fields to add/update
        remove_keys: Metadata keys to remove

    Returns:
        Updated note

    Example:
        >>> update_metadata_in_note(
        ...     "Note [paired:123] [old:value]",
        ...     {"paired": 456, "new": "data"},
        ...     {"old"}
        ... )
        "Note [paired:456] [new:data]"
    """
    clean_note, existing_metadata = decode_metadata_from_note(note)

    # Remove specified keys
    if remove_keys:
        for key in remove_keys:
            existing_metadata.pop(key, None)

    # Apply updates
    existing_metadata.update(updates)

    return encode_metadata_in_note(clean_note, existing_metadata)
