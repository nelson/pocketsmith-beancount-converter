import tempfile
from pathlib import Path
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
