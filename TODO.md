# PocketSmith to Beancount Converter - Project TODO

## Project Overview
Python 3-based program that retrieves information from PocketSmith and writes them to a beancount local cache.

## Progress Tracking

### ✅ Phase 1: Initial Setup (COMPLETED)
- [x] **Initialize uv project** - `uv init` completed
- [x] **Initialize git repository** - `git init` completed  
- [x] **Generate README.md** - Created comprehensive README in AGENTS.md format
- [x] **Add main dependencies** - Added `pocketsmith-api` and `beancount`
- [x] **Add development tools** - Added `ruff` and `pytest`

### ✅ Phase 2: Repository & Authentication (COMPLETED)
- [x] **Secure API key storage** - Created `.env` file with PocketSmith API key
- [x] **Environment security** - Added `.env` to `.gitignore` to prevent secret commits
- [x] **Updated documentation** - Modified README.md to reference `.env` file usage
- [x] **Create GitHub repository** - Ready for GitHub integration

### ✅ Phase 3: Core Development (COMPLETED)
- [x] **Generate core code to pull PocketSmith transactions**
  - ✅ Created `src/pocketsmith_beancount/pocketsmith_client.py`
  - ✅ Implemented API client with user-scoped endpoints
  - ✅ Added transaction, account, and category fetching functionality
- [x] **Generate code to convert transactions to beancount format**
  - ✅ Created `src/pocketsmith_beancount/beancount_converter.py`
  - ✅ Implemented transaction mapping logic with account sanitization
  - ✅ Added account/category mapping and multi-currency support
- [x] **Generate code to write beancount data locally**
  - ✅ Created `src/pocketsmith_beancount/file_writer.py`
  - ✅ Implemented local file writing with timestamped outputs
  - ✅ Added CLI interface in `src/pocketsmith_beancount/main.py`

### ✅ Phase 4: Quality Assurance (COMPLETED)
- [x] **Lint and format code with ruff**
  - ✅ Run `uv run ruff check .` - All checks passed
  - ✅ Run `uv run ruff format .` - All files formatted
  - ✅ Fixed all linting issues automatically
- [x] **Write unit tests with pytest**
  - ✅ Created `tests/test_pocketsmith_client.py` - 4 tests
  - ✅ Created `tests/test_beancount_converter.py` - 6 tests  
  - ✅ Created `tests/test_file_writer.py` - 6 tests
  - ✅ All 16 tests passing with good coverage
- [x] **End-to-end testing**
  - ✅ Successfully tested with real PocketSmith API data
  - ✅ Converted 30 transactions from January 2024
  - ✅ Generated valid Beancount format output

### ✅ Phase 5: Bug Fixes & Feature Enhancements (COMPLETED)

#### 🐛 Critical Bugs to Fix
- [x] **Fix commodities capitalization** - Use AUD, IDR, EUR instead of lowercase ✅ COMPLETED
- [x] **Fix account directives** - Use PocketSmith account names with IDs as metadata instead of "Unknown account" ✅ COMPLETED
- [x] **Add category account directives** - Create account directives for each PocketSmith category ✅ COMPLETED
- [x] **Fix payee/narration mapping** - Use PocketSmith Merchant as payee, Note as narration ✅ COMPLETED
- [x] **Add bean-check validation** - Integrate bean-check into pre-commit hook and GitHub workflow
- [x] **Add bean-check to local validation flow** - Run bean-check before pytest and ruff in development workflow ✅ COMPLETED
- [x] **Fix Beancount account name underscores** - Strip initial underscores from PocketSmith account names and convert spaces to hyphens ✅ COMPLETED
- [x] **Fix account declaration vs transaction name mismatch** - Account declarations show "Assets: Unknown: Account-blah" but transactions have correct names ✅ COMPLETED
- [x] **Change metadata key naming** - Use 'id' instead of 'pocketsmith_id' in metadata ✅ COMPLETED
- [x] **Add transaction IDs to metadata** - Transactions currently missing ID metadata ✅ COMPLETED

#### ✨ Missing Features to Implement
- [x] **Implement pagination** - Fetch transactions using pagination (1,000 per page) with Links header navigation ✅ COMPLETED
- [x] **Add PocketSmith metadata** - Include PocketSmith IDs as beancount metadata for accounts and categories ✅ COMPLETED
- [x] **Convert labels to tags** - Use PocketSmith transaction labels as beancount #tags ✅ COMPLETED
- [x] **Add needs_review flag** - Use PocketSmith needs_review field to add ! flag to transactions ✅ COMPLETED
- [x] **Fetch all transactions** - Ensure complete transaction retrieval (not just subset) ✅ COMPLETED
- [x] **Add balance directives** - Fetch and include balance directives from PocketSmith ✅ COMPLETED

#### 🔧 Quality Gates to Implement
- [x] **Add mypy to uv dependencies** - Start requiring mypy checks before local commits, and add it to the GitHub PR check workflow. Add it to the README. Start with `--strict`, and add `--ignore-missing-imports` if necessary. Fix any type errors ✅ COMPLETED
- [x] **Add pre-commit to uv dependencies** - Add current checks to pre-commit: mypy, pytest, bean-check, ruff ✅ COMPLETED



### ✅ Phase 6: Advanced File Management & Archive Features (COMPLETED)

#### 📁 Multi-File Beancount Structure
- [x] **Implement hierarchical file organization** - Create top-level beancount file with account declarations, category declarations, and includes ✅ COMPLETED
- [x] **Monthly transaction files** - Organize transactions into one file per month (YYYY-MM.beancount) ✅ COMPLETED
- [x] **Yearly folder structure** - Place monthly files in calendar year folders (e.g., 2024/2024-01.beancount) ✅ COMPLETED
- [x] **Update file writer** - Modify BeancountFileWriter to support multi-file output structure ✅ COMPLETED
- [x] **Add include statements** - Generate proper include directives in top-level file ✅ COMPLETED

#### 🔢 Data Type Improvements  
- [x] **Convert IDs to decimal numbers** - Change transaction and account IDs from strings to decimal numbers in beancount output ✅ COMPLETED
- [x] **Update metadata handling** - Ensure all ID fields use decimal representation consistently ✅ COMPLETED
- [x] **Validate decimal conversion** - Add error handling for invalid ID formats ✅ COMPLETED

#### 💰 Enhanced Account Declarations
- [x] **Use starting balance data** - Look for starting_balance and starting_balance_date in transaction account objects ✅ COMPLETED
- [x] **Account declaration dates** - Use starting_balance_date as the account declaration date when available ✅ COMPLETED
- [x] **Starting balance directives** - Include starting balance declarations in top-level beancount file ✅ COMPLETED
- [x] **Handle missing balance data** - Graceful fallback when starting balance information is not available ✅ COMPLETED

#### 📝 Transaction Changelog
- [x] **Implement compact changelog** - Create changelog file recording transaction operations ✅ COMPLETED
- [x] **Single-line format** - Use compact format instead of JSON for space efficiency ✅ COMPLETED
- [x] **AEST timestamps** - Include millisecond-resolution timestamps in Australian Eastern Standard Time ✅ COMPLETED
- [x] **Operation tracking** - Record create, modify, delete operations for transactions ✅ COMPLETED
- [x] **Field-level changes** - For modifications, specify which field changed with old and new values ✅ COMPLETED
- [x] **Example format** - `Aug 7 06:47:42.774 MODIFY 856546480 tags: [] -> #restaurants` ✅ COMPLETED

#### 🕒 Transaction Metadata Enhancements
- [x] **Last modified datetime** - Add metadata field using updated_at from transaction object ✅ COMPLETED
- [x] **AEST timezone handling** - Convert timestamps to Australian Eastern Standard Time ✅ COMPLETED
- [x] **Datetime format handling** - Try datetime.datetime first, fallback to string if needed ✅ COMPLETED
- [x] **Closing balance metadata** - Add closing_balance field as decimal number for future balance assertions ✅ COMPLETED

#### 🔄 Incremental Archive Updates
- [x] **Archive-based updates** - Replace full file rewrites with incremental updates to existing archive ✅ COMPLETED
- [x] **Transaction creation** - Handle new transactions from upstream service ✅ COMPLETED
- [x] **Transaction updates** - Detect and update modified transactions from upstream ✅ COMPLETED
- [x] **Metadata synchronization** - Ensure last modified datetime is updated for changed transactions ✅ COMPLETED
- [x] **Conflict resolution** - Handle cases where local and upstream data differ ✅ COMPLETED

## Current Status
**Phases 1-6 Complete** - PocketSmith-to-Beancount converter fully implemented with comprehensive test coverage and advanced file management features.

**✅ Phase 6 COMPLETED** - All advanced file management and archive features implemented:
- ✅ **26 of 26 Phase 6 features COMPLETED**
- ✅ **Hierarchical file structure with yearly folders and monthly transaction files**
- ✅ **Decimal ID format for all metadata fields with error handling**
- ✅ **Enhanced account declarations with starting balance data**
- ✅ **Compact transaction changelog with AEST timestamps**
- ✅ **Enhanced transaction metadata with last modified timestamps**
- ✅ **Incremental archive updates with change detection**
- ✅ **All tests passing (74 tests total)**
- ✅ **Type checking with mypy passing**
- ✅ **Code formatting and linting with ruff passing**

## Project Structure (Implemented)
```
├── .github/
│   └── workflows/
│       └── pr-checks.yml        # GitHub Actions CI/CD
├── src/
│   └── pocketsmith_beancount/
│       ├── __init__.py
│       ├── main.py              # CLI entry point ✅
│       ├── pocketsmith_client.py # PocketSmith API client ✅
│       ├── beancount_converter.py # Transaction converter ✅
│       └── file_writer.py       # Local file operations ✅
├── tests/
│   ├── __init__.py
│   ├── test_pocketsmith_client.py ✅ (10 tests)
│   ├── test_beancount_converter.py ✅ (23 tests)
│   ├── test_file_writer.py      ✅ (10 tests)
│   ├── test_main.py             ✅ (6 tests)
│   └── test_integration.py      ✅ (4 tests)
├── output/                      # Generated Beancount files
├── .env                         # API key storage (gitignored)
├── .gitignore                   # Updated with .env
├── pyproject.toml
├── README.md                    # Updated with .env usage
└── TODO.md (this file)
```

## Dependencies Added
- **Main**: `requests`, `python-dotenv`, `beancount`
- **Dev**: `ruff`, `pytest`, `mypy`, `types-requests`, `pre-commit`

## Features Status

### ✅ Implemented Features
- ✅ Secure API key management with `.env` files
- ✅ PocketSmith API client with user-scoped endpoints
- ✅ Basic Beancount format converter with account mapping
- ✅ Local file writer with timestamped outputs
- ✅ CLI interface with date range filtering
- ✅ **Comprehensive test suite (53 tests passing)**
- ✅ GitHub Actions CI/CD pipeline
- ✅ Multi-currency support with proper capitalization
- ✅ Account name sanitization and mapping
- ✅ End-to-end workflow tested with real data

### 🐛 Known Issues
- ✅ Commodities use lowercase instead of uppercase (aud → AUD) - FIXED
- ✅ Account directives show "Unknown account" instead of PocketSmith names - FIXED
- ✅ Missing account directives for PocketSmith categories - FIXED
- ✅ Same string used for both payee and narration - FIXED
- ❌ No bean-check validation in CI/CD

### ✅ Implemented Features (All Complete)
- ✅ Pagination for large transaction sets - IMPLEMENTED
- ✅ PocketSmith IDs as beancount metadata - IMPLEMENTED
- ✅ Transaction labels as beancount tags - IMPLEMENTED
- ✅ needs_review flag support - IMPLEMENTED
- ✅ Complete transaction fetching - IMPLEMENTED
- ✅ Balance directives - IMPLEMENTED

## Usage
```bash
# Basic usage
uv run python -m src.pocketsmith_beancount.main

# With date range
uv run python -m src.pocketsmith_beancount.main --start-date 2024-01-01 --end-date 2024-01-31

# Development commands
uv run pytest                    # Run tests
uv run ruff check .             # Lint code
uv run ruff format .            # Format code
uv run bean-check output/main.beancount   # Validate beancount files (after implementing)
```
