# PocketSmith to Beancount Converter

A comprehensive Python tool to retrieve transaction data from PocketSmith, convert it to Beancount format, and automate transaction processing with intelligent rules for categorization and enrichment.

## Overview

This project provides a comprehensive way to:
- **Fetch transaction data** from PocketSmith via their API with pagination support
- **Convert transactions** to Beancount format with proper account mapping
- **Apply intelligent rules** for automated transaction categorization and enrichment
- **Synchronize bidirectionally** between PocketSmith and local Beancount files
- **Include rich metadata** with PocketSmith IDs, labels as tags, and review flags
- **Validate output** with bean-check integration
- **Store data locally** for accounting and analysis with hierarchical file organization

## Features

### 🔄 Data Synchronization
- **Modern CLI**: Phase 9 introduces `clone`, `pull`, and `diff` commands with intelligent sync capabilities
- **Complete data sync**: Fetches all transactions, accounts, categories, and balances
- **Incremental updates**: `pull` command uses `updated_since` parameter for efficient syncing
- **Smart updates**: Uses field resolver strategies instead of naive overwrite during pull operations
- **Difference detection**: `diff` command compares local and remote data without modifying anything
- **Change detection**: Automatic detection of new and modified transactions with detailed logging
- **Bidirectional synchronization**: Keep PocketSmith and beancount data in sync with intelligent conflict resolution
- **Field-specific resolution**: Different sync strategies for different data types (amounts, notes, categories, tags)
- **Write-back support**: Update PocketSmith via REST API when local changes are detected
- **Pagination**: Handles large datasets with automatic pagination

### 📋 Transaction Rules (Phase 8 ✅)
- **YAML rule definitions**: Define rules with flexible if/then logic for automated processing
- **Pattern matching**: Regex-based matching on account, category, and merchant fields  
- **Smart transforms**: Automatic category assignment, label management, memo updates, and metadata enrichment
- **Priority ordering**: Rules applied by ID with first-match semantics
- **Interactive rule creation**: CLI tools for creating rules interactively or via command line
- **Dry-run support**: Preview rule applications before making changes

### 🗂️ File Organization  
- **Proper formatting**: Uses correct commodity capitalization and account names
- **Hierarchical file structure**: Organize transactions by year/month with top-level declarations
- **Rich metadata**: Includes PocketSmith IDs, labels as tags, and review flags
- **Enhanced metadata**: Last modified timestamps, closing balances, and decimal ID format
- **Transaction changelog**: Comprehensive change tracking with timestamped logs for CLONE, PULL, and OVERWRITE operations
- **Flexible output**: Support for both single-file and hierarchical output structures

### 🛠️ Development & Validation
- **Modern CLI interface**: Phase 9 introduces `clone`, `pull`, and `diff` commands with comprehensive options
- **Default file detection**: Automatically finds main.beancount or .beancount with matching .log file
- **Legacy CLI support**: Backward compatible sync, apply, and add-rule commands
- **Validation**: Integrated bean-check validation for output files
- **Dry-run support**: Preview changes before applying them with `--dry-run` option
- **Verbose mode**: Detailed output with `-v` flag for pull operations
- **Comprehensive testing**: 450+ tests including property-based and integration testing

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

The tool uses a **command-based interface** for better organization of functionality. Phase 9 introduces an improved CLI with the new `clone` command powered by typer.

### Clone Command (Phase 9 ✅)

The `clone` command provides a modern, flexible interface for downloading PocketSmith data and creating a new ledger with changelog:

```bash
# Clone transactions (auto-detects local beancount files if no destination provided)
uv run python main.py clone

# Download to hierarchical structure (default: output/ with main.beancount and main.log)
uv run python main.py clone output/

# Download to single file with changelog
uv run python main.py clone -1 transactions.beancount  # Creates transactions.log

# Download with date range
uv run python main.py clone --from 2024-01-01 --to 2024-12-31 output/

# Download current month
uv run python main.py clone --this-month output/

# Download last year  
uv run python main.py clone --last-year output/

# Quiet mode (suppress informational output)
uv run python main.py clone --quiet output/
```

### Pull Command (Phase 9 ✅)

The `pull` command updates an existing ledger with recent PocketSmith data, using intelligent sync and change tracking with field resolver strategies:

```bash
# Update existing ledger (auto-detects local files)
uv run python main.py pull

# Update specific ledger with recent changes
uv run python main.py pull output/

# Update with dry-run (preview changes)
uv run python main.py pull --dry-run output/

# Update with verbose mode (shows UPDATE entries)
uv run python main.py pull -v output/

# Combine dry-run and verbose to preview updates
uv run python main.py pull -n -v output/

# Pull specific date range (expands sync scope)
uv run python main.py pull --from 2024-02-01 --to 2024-02-29 output/

# Pull current month
uv run python main.py pull --this-month output/

# Quiet mode
uv run python main.py pull --quiet output/
```

### Diff Command (Phase 9 ✅)

The `diff` command compares local and remote data without making any changes:

```bash
# Compare local and remote data (auto-detects local files)
uv run python main.py diff

# Compare specific ledger
uv run python main.py diff output/

# Show summary of differences (default)
uv run python main.py diff --format summary output/

# Show only transaction IDs that differ
uv run python main.py diff --format ids output/

# Show differences in changelog format
uv run python main.py diff --format changelog output/

# Show differences in traditional diff format
uv run python main.py diff --format diff output/

# Compare specific date range
uv run python main.py diff --from 2024-01-01 --to 2024-01-31 output/

# Compare current month
uv run python main.py diff --this-month output/

# Compare last year
uv run python main.py diff --last-year output/
```

### Data Synchronization (Legacy)

```bash
# Download and convert transactions (single file)
uv run python -m src.pocketsmith_beancount.main sync

# Download with specific date range
uv run python -m src.pocketsmith_beancount.main sync --start-date 2024-01-01 --end-date 2024-12-31

# Use hierarchical file structure (recommended for large datasets)
uv run python -m src.pocketsmith_beancount.main sync --hierarchical

# Bidirectional synchronization between PocketSmith and beancount
uv run python -m src.pocketsmith_beancount.main sync --sync

# Sync with dry-run mode (preview changes without applying them)
uv run python -m src.pocketsmith_beancount.main sync --sync --dry-run

# Sync with verbose logging and custom output directory
uv run python -m src.pocketsmith_beancount.main sync --sync --sync-verbose --output-dir /path/to/output
```

### Transaction Rules (Phase 8 ✅)

```bash
# Apply rules to transactions
uv run python -m src.pocketsmith_beancount.main apply --rules-file rules.yaml

# Apply rules with dry-run to preview changes
uv run python -m src.pocketsmith_beancount.main apply --rules-file rules.yaml --dry-run

# Apply rules to specific transactions only
uv run python -m src.pocketsmith_beancount.main apply --rules-file rules.yaml --transaction-ids 123 456 789

# Create a new rule interactively
uv run python -m src.pocketsmith_beancount.main add-rule --interactive

# Create a rule via command line
uv run python -m src.pocketsmith_beancount.main add-rule --rule-id 1 --merchant "Starbucks" --new-category "Dining" --labels "coffee,beverages"
```

### Rule File Example

Create a `rules.yaml` file for automated transaction processing:

```yaml
- id: 1
  if:
    - merchant: "McDonalds"
  then:
    - category: "Dining"
    - labels: ["fast-food", "restaurants"]

- id: 2
  if:
    - merchant: "UNITED AIRLINES"
  then:
    - category: "Transport"
    - labels: ["flights", "business"]
    - metadata:
        expense_type: "business"
        reimbursable: true

- id: 3
  if:
    - account: "credit"
    - merchant: "Amazon"
  then:
    - category: "Shopping"
    - memo: "Online purchase"
```

## Development

### Dependencies
- `requests`: HTTP client for PocketSmith API
- `python-dotenv`: Environment variable management
- `beancount`: Beancount library for financial data validation
- `pytz`: Timezone handling for AEST timestamps
- `PyYAML`: YAML parsing for rule definitions
- `regex`: Advanced regex features for pattern matching
- `colorama`: Colored terminal output for enhanced UX

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

