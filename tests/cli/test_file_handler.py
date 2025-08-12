"""Tests for file handling utilities."""

import pytest
import tempfile
import os
from pathlib import Path
from src.cli.file_handler import (
    validate_output_destination,
    ensure_beancount_extension,
    create_hierarchical_structure,
    get_output_file_path,
    FileHandlerError,
)


class TestValidateOutputDestination:
    """Test output destination validation."""

    def test_validate_new_file_destination(self):
        """Test validating new file destination."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "new_file.beancount"
            result = validate_output_destination(dest_path, single_file=True)
            assert result == dest_path

    def test_validate_new_directory_destination(self):
        """Test validating new directory destination."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "new_directory"
            result = validate_output_destination(dest_path, single_file=False)
            assert result == dest_path

    def test_validate_existing_file_fails(self):
        """Test that existing file destination fails."""
        with tempfile.NamedTemporaryFile() as temp_file:
            dest_path = Path(temp_file.name)
            with pytest.raises(FileHandlerError, match="File .* already exists"):
                validate_output_destination(dest_path, single_file=True)

    def test_validate_existing_directory_fails(self):
        """Test that existing directory destination fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir)
            with pytest.raises(FileHandlerError, match="Directory .* already exists"):
                validate_output_destination(dest_path, single_file=False)

    def test_validate_creates_parent_directory(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "new_parent" / "new_file.beancount"
            result = validate_output_destination(dest_path, single_file=True)
            assert result == dest_path
            assert dest_path.parent.exists()

    def test_validate_unwritable_parent_fails(self):
        """Test that unwritable parent directory fails."""
        # This test is platform-dependent and may not work on all systems
        if os.name == "posix":  # Unix-like systems
            with tempfile.TemporaryDirectory() as temp_dir:
                parent_dir = Path(temp_dir) / "readonly_parent"
                parent_dir.mkdir()
                parent_dir.chmod(0o444)  # Read-only

                dest_path = parent_dir / "new_file.beancount"
                try:
                    with pytest.raises(FileHandlerError, match="Permission denied"):
                        validate_output_destination(dest_path, single_file=True)
                finally:
                    parent_dir.chmod(0o755)  # Restore permissions for cleanup


class TestEnsureBeancountExtension:
    """Test beancount extension handling."""

    def test_add_extension_when_missing(self):
        """Test adding .beancount extension when missing."""
        path = Path("transactions")
        result = ensure_beancount_extension(path)
        assert result == Path("transactions.beancount")

    def test_keep_extension_when_present(self):
        """Test keeping .beancount extension when already present."""
        path = Path("transactions.beancount")
        result = ensure_beancount_extension(path)
        assert result == Path("transactions.beancount")

    def test_replace_different_extension(self):
        """Test replacing different extension with .beancount."""
        path = Path("transactions.txt")
        result = ensure_beancount_extension(path)
        assert result == Path("transactions.beancount")

    def test_handle_multiple_dots(self):
        """Test handling filenames with multiple dots."""
        path = Path("my.transactions.data")
        result = ensure_beancount_extension(path)
        assert result == Path("my.transactions.beancount")


class TestCreateHierarchicalStructure:
    """Test hierarchical directory structure creation."""

    def test_create_new_directory(self):
        """Test creating new directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "new_structure"
            create_hierarchical_structure(base_dir)
            assert base_dir.exists()
            assert base_dir.is_dir()

    def test_create_nested_directories(self):
        """Test creating nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            create_hierarchical_structure(base_dir)
            assert base_dir.exists()
            assert base_dir.is_dir()

    def test_create_existing_directory_succeeds(self):
        """Test that creating existing directory succeeds."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            # Should not raise an error
            create_hierarchical_structure(base_dir)
            assert base_dir.exists()


class TestGetOutputFilePath:
    """Test output file path generation."""

    def test_single_file_path(self):
        """Test getting single file output path."""
        destination = Path("output")
        result = get_output_file_path(destination, single_file=True)
        assert result == Path("output.beancount")

    def test_single_file_path_with_extension(self):
        """Test getting single file path when extension already present."""
        destination = Path("output.beancount")
        result = get_output_file_path(destination, single_file=True)
        assert result == Path("output.beancount")

    def test_hierarchical_file_path(self):
        """Test getting hierarchical file output path."""
        destination = Path("output_dir")
        result = get_output_file_path(destination, single_file=False)
        assert result == Path("output_dir") / "main.beancount"

    def test_hierarchical_file_path_complex(self):
        """Test getting hierarchical file path with complex destination."""
        destination = Path("path") / "to" / "output_dir"
        result = get_output_file_path(destination, single_file=False)
        assert result == Path("path") / "to" / "output_dir" / "main.beancount"


class TestFileHandlerEdgeCases:
    """Test edge cases in file handling."""

    def test_validate_string_path(self):
        """Test validating string path (not Path object)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "new_file.beancount")
            result = validate_output_destination(dest_path, single_file=True)
            assert result == Path(dest_path)

    def test_ensure_extension_empty_path(self):
        """Test ensuring extension on empty path."""
        path = Path("")
        result = ensure_beancount_extension(path)
        assert result == Path(".beancount")

    def test_ensure_extension_dot_only(self):
        """Test ensuring extension on path with just a dot."""
        path = Path(".")
        result = ensure_beancount_extension(path)
        assert result == Path(".beancount")

    def test_create_structure_permission_error(self):
        """Test handling permission errors during directory creation."""
        # This test is platform-dependent
        if os.name == "posix":  # Unix-like systems
            with tempfile.TemporaryDirectory() as temp_dir:
                readonly_dir = Path(temp_dir) / "readonly"
                readonly_dir.mkdir()
                readonly_dir.chmod(0o444)  # Read-only

                nested_dir = readonly_dir / "nested"
                try:
                    with pytest.raises(
                        FileHandlerError, match="Cannot create directory"
                    ):
                        create_hierarchical_structure(nested_dir)
                finally:
                    readonly_dir.chmod(0o755)  # Restore permissions for cleanup
