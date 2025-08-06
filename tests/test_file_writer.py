import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from src.pocketsmith_beancount.file_writer import BeancountFileWriter


class TestBeancountFileWriter:
    def test_init_default_output_dir(self):
        writer = BeancountFileWriter()
        assert writer.output_dir == Path("./output")

    def test_init_custom_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)
            assert writer.output_dir == Path(temp_dir)

    def test_write_beancount_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)
            content = "2024-01-01 open Assets:Checking USD"

            file_path = writer.write_beancount_file(content, "test")

            assert file_path.endswith("test.beancount")
            assert Path(file_path).exists()

            with open(file_path, "r") as f:
                assert f.read() == content

    def test_write_beancount_file_auto_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)
            content = "2024-01-01 open Assets:Checking USD"

            file_path = writer.write_beancount_file(content)

            assert "pocketsmith_transactions_" in file_path
            assert file_path.endswith(".beancount")
            assert Path(file_path).exists()

    def test_append_to_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)

            initial_content = "2024-01-01 open Assets:Checking USD"
            file_path = writer.write_beancount_file(initial_content, "test")

            additional_content = '2024-01-02 * "Test" "Test transaction"'
            writer.append_to_file(additional_content, "test.beancount")

            with open(file_path, "r") as f:
                content = f.read()
                assert initial_content in content
                assert additional_content in content

    def test_get_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)
            assert writer.get_output_directory() == temp_dir

    def test_init_with_env_var(self):
        """Test initialization with BEANCOUNT_OUTPUT_DIR environment variable"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"BEANCOUNT_OUTPUT_DIR": temp_dir}):
                writer = BeancountFileWriter()
                assert writer.output_dir == Path(temp_dir)

    def test_write_file_creates_directory(self):
        """Test that output directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested directory path that doesn't exist
            nested_dir = Path(temp_dir) / "nested" / "output"
            writer = BeancountFileWriter(str(nested_dir))

            # Directory should be created during initialization
            assert nested_dir.exists()

            # Should be able to write files
            content = "2024-01-01 open Assets:Checking USD"
            file_path = writer.write_beancount_file(content, "test")
            assert Path(file_path).exists()

    def test_write_file_with_extension_already_present(self):
        """Test filename handling when .beancount extension already exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)
            content = "2024-01-01 open Assets:Checking USD"

            # Pass filename that already has .beancount extension
            file_path = writer.write_beancount_file(content, "test.beancount")

            # Should not double the extension
            assert file_path.endswith("test.beancount")
            assert not file_path.endswith("test.beancount.beancount")
            assert Path(file_path).exists()

    def test_append_to_nonexistent_file(self):
        """Test appending to a file that doesn't exist yet"""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = BeancountFileWriter(temp_dir)

            # Try to append to a file that doesn't exist
            content = "2024-01-01 open Assets:Checking USD"
            file_path = writer.append_to_file(content, "nonexistent.beancount")

            # File should be created and content should be written
            assert Path(file_path).exists()

            with open(file_path, "r") as f:
                file_content = f.read()
                # Should have leading newlines from append operation
                assert content in file_content
                assert file_content.startswith("\n\n")
