# PocketSmith to Beancount Converter

A Python tool to retrieve transaction data from PocketSmith and convert it to Beancount format for local storage and accounting.

## Overview

This project provides a comprehensive way to:
- Fetch transaction data from PocketSmith via their API with pagination support
- Convert transactions to Beancount format with proper account mapping
- Include PocketSmith metadata, labels as tags, and review flags
- Validate output with bean-check integration
- Store the data locally for accounting and analysis

## Features

- **Complete data sync**: Fetches all transactions, accounts, categories, and balances
- **Proper formatting**: Uses correct commodity capitalization and account names
- **Rich metadata**: Includes PocketSmith IDs, labels as tags, and review flags
- **Validation**: Integrated bean-check validation for output files
- **Pagination**: Handles large datasets with automatic pagination
- **CLI interface**: Date range filtering and flexible configuration
- **Hierarchical file structure**: Organize transactions by year/month with top-level declarations
- **Transaction changelog**: Track changes with compact AEST timestamped logs
- **Enhanced metadata**: Last modified timestamps, closing balances, and decimal ID format
- **Incremental updates**: Support for archive-based updates with change detection

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up your PocketSmith API key:
   Create a `.env` file in the project root with your API key:
   ```
   POCKETSMITH_API_KEY=your_api_key_here
   ```

## Usage

```bash
# Fetch and convert transactions (single file)
uv run python -m src.pocketsmith_beancount.main

# Run with specific date range
uv run python -m src.pocketsmith_beancount.main --start-date 2024-01-01 --end-date 2024-12-31

# Use hierarchical file structure (recommended for large datasets)
uv run python -m src.pocketsmith_beancount.main --hierarchical

# Specify custom output directory
uv run python -m src.pocketsmith_beancount.main --output-dir /path/to/output --hierarchical
```

## Development

### Dependencies
- `requests`: HTTP client for PocketSmith API
- `python-dotenv`: Environment variable management
- `beancount`: Beancount library for financial data validation
- `pytz`: Timezone handling for AEST timestamps

### Development Tools
- `ruff`: Linting and formatting
- `pytest`: Testing framework
- `mypy`: Static type checking with strict mode
- `pre-commit`: Git hooks for quality gates
- `bean-check`: Beancount file validation (part of beancount package)

### Commands

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run type checking
uv run mypy src/

# Run tests
uv run pytest

# Validate beancount files
uv run bean-check output/main.beancount

# Run pre-commit hooks
uv run pre-commit run --all-files

# Run all checks manually
uv run ruff check . && uv run ruff format . && uv run mypy src/ && uv run pytest && uv run bean-check output/main.beancount
```

## Project Structure

```
├── src/
│   └── pocketsmith_beancount/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── pocketsmith_client.py # PocketSmith API client
│       ├── beancount_converter.py # Transaction converter
│       ├── file_writer.py       # Local file operations
│       └── changelog.py         # Transaction change tracking
├── tests/
│   ├── __init__.py
│   ├── test_pocketsmith_client.py
│   ├── test_beancount_converter.py
│   ├── test_file_writer.py
│   ├── test_main.py
│   └── test_integration.py
├── output/                      # Generated files (hierarchical mode)
│   ├── main.beancount          # Top-level declarations and includes
│   ├── changelog.txt           # Transaction change log
│   └── 2024/                   # Yearly folders
│       ├── 2024-01.beancount   # Monthly transaction files
│       └── 2024-02.beancount
├── pyproject.toml
└── README.md
```

## Configuration

The tool supports configuration via environment variables:
- `POCKETSMITH_API_KEY`: Your PocketSmith API key (required)
- `BEANCOUNT_OUTPUT_DIR`: Directory for output files (default: ./output)
- `POCKETSMITH_BASE_URL`: API base URL (default: https://api.pocketsmith.com/v2)

## API Requirements

You'll need a PocketSmith API key. Get one from:
1. Log into your PocketSmith account
2. Go to Settings → Developer
3. Generate a new API key

## CONTRIBUTION

### Contribution Checklist

This checklist should be followed for every code contribution submitted to GitHub.

- [ ] Summarise changes from beginning of session
- [ ] Create GitHub issue
- [ ] Create well named branch
- [ ] Commit changes with message that follows this exact format:
  - **First line**: `<type>: #[ISSUE_NUMBER] [SUMMARY]`
    - `<type>` follows [Conventional Commits](https://www.conventionalcommits.org) (feat, fix, docs, etc.)
    - `[ISSUE_NUMBER]` is the GitHub issue number (e.g., #17)
    - `[SUMMARY]` is a concise one-line description
  - **Body**: Detailed description with bullet points of changes
  - **Final line**: `Closes #[ISSUE_NUMBER]`
- [ ] Create GitHub pull request based on this branch and link to the GitHub issue
- [ ] Poll for the pull request status
  - If successful, pull and checkout master, and clean up branches
  - If failed, don't pull, stay on the branch and try to fix any issues

