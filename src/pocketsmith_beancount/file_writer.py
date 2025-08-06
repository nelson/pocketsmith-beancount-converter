import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class BeancountFileWriter:
    def __init__(self, output_dir: Optional[str] = None):
        output_path = output_dir or os.getenv("BEANCOUNT_OUTPUT_DIR") or "./output"
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_beancount_file(self, content: str, filename: Optional[str] = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pocketsmith_transactions_{timestamp}.beancount"

        if not filename.endswith(".beancount"):
            filename += ".beancount"

        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def append_to_file(self, content: str, filename: str) -> str:
        file_path = self.output_dir / filename

        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)

        return str(file_path)

    def get_output_directory(self) -> str:
        return str(self.output_dir)
