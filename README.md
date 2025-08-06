# PocketSmith to Beancount Converter

A Python tool to retrieve transaction data from PocketSmith and convert it to Beancount format for local storage and accounting.

## Overview

This project provides a seamless way to:
- Fetch transaction data from PocketSmith via their API
- Convert transactions to Beancount format
- Store the data locally for accounting and analysis

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
- `pocketsmith-api`: PocketSmith API client
- `beancount`: Beancount library for financial data

### Development Tools
- `ruff`: Linting and formatting
- `pytest`: Testing framework

### Commands

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run tests
uv run pytest

# Run all checks
uv run ruff check . && uv run ruff format . && uv run pytest
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