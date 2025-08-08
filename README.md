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
- **Bidirectional synchronization**: Keep PocketSmith and beancount data in sync with intelligent conflict resolution
- **Field-specific resolution**: Different sync strategies for different data types (amounts, notes, categories, tags)
- **Write-back support**: Update PocketSmith via REST API when local changes are detected

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

### Basic Operations

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

### Synchronization Operations

```bash
# Synchronize changes between PocketSmith and beancount
uv run python -m src.pocketsmith_beancount.main --sync

# Sync with dry-run mode (show what would be changed without making changes)
uv run python -m src.pocketsmith_beancount.main --sync --dry-run

# Sync with verbose logging for detailed operation tracking
uv run python -m src.pocketsmith_beancount.main --sync --sync-verbose

# Sync with custom batch size for API operations
uv run python -m src.pocketsmith_beancount.main --sync --sync-batch-size 50

# Combine sync with hierarchical structure and date range
uv run python -m src.pocketsmith_beancount.main --sync --hierarchical --start-date 2024-01-01
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
│       ├── pocketsmith_client.py # PocketSmith API client (with PUT/PATCH support)
│       ├── beancount_converter.py # Transaction converter
│       ├── file_writer.py       # Local file operations
│       ├── changelog.py         # Transaction change tracking
│       ├── synchronizer.py      # Main synchronization orchestrator
│       ├── field_resolver.py    # Field resolution strategies
│       ├── field_mapping.py     # Field-to-strategy mapping
│       ├── resolution_engine.py # Resolution strategy orchestration
│       ├── transaction_comparator.py # Transaction comparison logic
│       ├── api_writer.py        # REST API write-back functionality
│       ├── sync_models.py       # Synchronization data structures
│       ├── sync_enums.py        # Synchronization enums and constants
│       ├── sync_exceptions.py   # Synchronization error classes
│       ├── sync_interfaces.py   # Synchronization interfaces
│       └── sync_cli.py          # CLI synchronization handler
├── tests/
│   ├── __init__.py
│   ├── test_pocketsmith_client.py
│   ├── test_beancount_converter.py
│   ├── test_file_writer.py
│   ├── test_main.py
│   ├── test_integration.py
│   ├── test_synchronizer.py     # Sync orchestrator tests
│   ├── test_field_resolver.py   # Resolution strategy tests
│   ├── test_transaction_comparator.py # Comparison logic tests
│   ├── test_api_writer.py       # Write-back functionality tests
│   ├── test_sync_models.py      # Sync data structure tests
│   ├── test_sync_cli.py         # CLI sync handler tests
│   ├── test_real_api_endpoints.py # Real API validation tests
│   ├── test_property_based.py   # Property-based tests with hypothesis
│   ├── test_data_validation.py  # Comprehensive data validation tests
│   └── test_edge_cases.py       # Edge case and error handling tests
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

## Synchronization

The synchronization feature keeps PocketSmith and beancount data in sync using intelligent field-specific resolution strategies. This bidirectional sync ensures your data stays consistent across both systems while respecting the nature of different data types.

### How Synchronization Works

1. **Transaction Matching**: Transactions are matched between PocketSmith and beancount using unique IDs
2. **Change Detection**: The system compares timestamps and content to identify what has changed
3. **Conflict Resolution**: Different resolution strategies are applied based on the field type
4. **Bidirectional Updates**: Changes are applied to both local beancount files and remote PocketSmith data
5. **Comprehensive Logging**: All sync operations are logged with detailed field-level changes

### Resolution Strategies

The sync system uses 5 different strategies for handling conflicts:

#### Strategy 1: Never Change (Immutable Fields)
- **Fields**: Transaction amounts, account names, closing balances, transaction titles
- **Behavior**: These fields should never change. Conflicts generate warnings but no updates occur
- **Rationale**: Core financial data should remain stable to maintain data integrity

#### Strategy 2: Local Changes Only (Write-back Fields)  
- **Fields**: Transaction notes/narration
- **Behavior**: Local changes are written back to PocketSmith, remote changes are ignored
- **Rationale**: Notes are often enhanced locally and should be preserved in the remote system

#### Strategy 3: Remote Changes Only (Overwrite Fields)
- **Fields**: Last modified timestamps, system-generated metadata
- **Behavior**: Remote changes overwrite local values
- **Rationale**: System timestamps should reflect the authoritative remote state

#### Strategy 4: Remote Wins (Remote Priority Fields)
- **Fields**: Transaction categories
- **Behavior**: Remote changes take precedence over local modifications
- **Rationale**: Categories are typically managed in PocketSmith and should be authoritative

#### Strategy 5: Merge Lists (Bidirectional Merge Fields)
- **Fields**: Transaction labels/tags
- **Behavior**: Local and remote changes are merged with deduplication
- **Rationale**: Tags can be added from either system and should be combined

### Field Mapping

| Field Type | Strategy | Local → Remote | Remote → Local |
|------------|----------|----------------|----------------|
| Title, Amount, Account, Closing Balance | Strategy 1 | ❌ (warn) | ❌ (warn) |
| Note/Narration | Strategy 2 | ✅ (write-back) | ❌ (ignore) |
| Last Modified, System Metadata | Strategy 3 | ❌ (ignore) | ✅ (overwrite) |
| Category | Strategy 4 | ❌ (ignore) | ✅ (overwrite) |
| Labels/Tags | Strategy 5 | ✅ (merge) | ✅ (merge) |

### Sync Modes

- **Full Sync**: `--sync` - Perform complete synchronization between systems
- **Dry Run**: `--sync --dry-run` - Preview changes without making any updates
- **Verbose**: `--sync --sync-verbose` - Detailed logging of all sync operations
- **Batch Size**: `--sync --sync-batch-size N` - Control API batch size for performance tuning

## API Requirements

You'll need a PocketSmith API key. Get one from:
1. Log into your PocketSmith account
2. Go to Settings → Developer
3. Generate a new API key

