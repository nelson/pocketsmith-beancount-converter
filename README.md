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
# Fetch and convert transactions
python -m pocketsmith_beancount.main

# Run with specific date range
python -m pocketsmith_beancount.main --start-date 2024-01-01 --end-date 2024-12-31
```

## Development

### Dependencies
- `requests`: HTTP client for PocketSmith API
- `python-dotenv`: Environment variable management
- `beancount`: Beancount library for financial data validation

### Development Tools
- `ruff`: Linting and formatting
- `pytest`: Testing framework
- `bean-check`: Beancount file validation (part of beancount package)

### Commands

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run tests
uv run pytest

# Validate beancount files
uv run bean-check output/*.beancount

# Run all checks
uv run ruff check . && uv run ruff format . && uv run pytest && uv run bean-check output/*.beancount
```

## Project Structure

```
├── src/
│   └── pocketsmith_beancount/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── pocketsmith_client.py # PocketSmith API client
│       ├── beancount_converter.py # Transaction converter
│       └── file_writer.py       # Local file operations
├── tests/
│   ├── __init__.py
│   ├── test_pocketsmith_client.py
│   ├── test_beancount_converter.py
│   └── test_file_writer.py
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