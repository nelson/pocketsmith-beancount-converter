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

### 🔄 Phase 5: Bug Fixes & Feature Enhancements (IN PROGRESS)

#### 🐛 Critical Bugs to Fix
- [x] **Fix commodities capitalization** - Use AUD, IDR, EUR instead of lowercase ✅ COMPLETED
- [x] **Fix account directives** - Use PocketSmith account names with IDs as metadata instead of "Unknown account" ✅ COMPLETED
- [x] **Add category account directives** - Create account directives for each PocketSmith category ✅ COMPLETED
- [x] **Fix payee/narration mapping** - Use PocketSmith Merchant as payee, Note as narration ✅ COMPLETED
- [ ] **Add bean-check validation** - Integrate bean-check into pre-commit hook and GitHub workflow
- [x] **Add bean-check to local validation flow** - Run bean-check before pytest and ruff in development workflow ✅ COMPLETED
- [x] **Fix Beancount account name underscores** - Strip initial underscores from PocketSmith account names and convert spaces to hyphens ✅ COMPLETED
- [x] **Fix account declaration vs transaction name mismatch** - Account declarations show "Assets: Unknown: Account-blah" but transactions have correct names ✅ COMPLETED
- [x] **Change metadata key naming** - Use 'id' instead of 'pocketsmith_id' in metadata ✅ COMPLETED
- [x] **Add transaction IDs to metadata** - Transactions currently missing ID metadata ✅ COMPLETED

#### ✨ Missing Features to Implement
- [ ] **Implement pagination** - Fetch transactions using pagination (1,000 per page) with Links header navigation
- [x] **Add PocketSmith metadata** - Include PocketSmith IDs as beancount metadata for accounts and categories ✅ COMPLETED
- [ ] **Convert labels to tags** - Use PocketSmith transaction labels as beancount #tags
- [ ] **Add needs_review flag** - Use PocketSmith needs_review field to add ! flag to transactions
- [ ] **Fetch all transactions** - Ensure complete transaction retrieval (not just subset)
- [ ] **Add balance directives** - Fetch and include balance directives from PocketSmith

#### 🔧 Quality Gates to Implement
- [x] **Add mypy to uv dependencies** - Start requiring mypy checks before local commits, and add it to the GitHub PR check workflow. Add it to the README. Start with `--strict`, and add `--ignore-missing-imports` if necessary. Fix any type errors ✅ COMPLETED
- [x] **Add pre-commit to uv dependencies** - Add current checks to pre-commit: mypy, pytest, bean-check, ruff ✅ COMPLETED

#### 🧪 Testing Requirements
- [ ] **Write unit tests for bug fixes** - Comprehensive test coverage for all bug fixes
- [ ] **Write unit tests for new features** - Test coverage for all new functionality

#### 🧪 Missing Unit Tests Analysis (Current: 22 tests)

##### **PocketSmithClient Tests** (4 current tests)
**Missing:**
- [ ] **`test_get_accounts()`** - Test fetching user accounts
- [ ] **`test_get_categories()`** - Test fetching user categories  
- [ ] **`test_get_transaction_accounts()`** - Test fetching transaction accounts
- [ ] **`test_make_request_error_handling()`** - Test HTTP error handling (404, 401, 500)
- [ ] **`test_get_transactions_without_params()`** - Test transactions without date/account filters
- [ ] **`test_api_response_type_handling()`** - Test handling of non-list responses from API

##### **BeancountConverter Tests** (12 current tests)
**Missing:**
- [ ] **`test_get_category_account_transfer()`** - Test transfer category handling
- [ ] **`test_get_category_account_none()`** - Test null/missing category handling
- [ ] **`test_get_account_name_credit_card()`** - Test credit card account type mapping to Liabilities
- [ ] **`test_get_account_name_loan()`** - Test loan account type mapping to Liabilities
- [ ] **`test_get_account_name_missing_institution()`** - Test accounts without institution data
- [ ] **`test_convert_transaction_missing_category()`** - Test transactions without categories
- [ ] **`test_convert_transaction_missing_transaction_account()`** - Test transactions without account data
- [ ] **`test_convert_transaction_quote_escaping()`** - Test payee/narration with quotes
- [ ] **`test_convert_transactions_full_integration()`** - Test the full `convert_transactions()` method
- [ ] **`test_generate_account_declarations_missing_dates()`** - Test accounts without starting_balance_date
- [ ] **`test_generate_commodity_declarations_empty()`** - Test when no currencies are tracked

##### **BeancountFileWriter Tests** (6 current tests)
**Missing:**
- [ ] **`test_init_with_env_var()`** - Test initialization with BEANCOUNT_OUTPUT_DIR environment variable
- [ ] **`test_write_file_creates_directory()`** - Test that output directory is created if it doesn't exist
- [ ] **`test_write_file_with_extension_already_present()`** - Test filename handling when .beancount extension already exists
- [ ] **`test_append_to_nonexistent_file()`** - Test appending to a file that doesn't exist yet

##### **Main Module Tests** (0 current tests) - **HIGH PRIORITY**
**Missing:**
- [ ] **`test_main_argument_parsing()`** - Test CLI argument parsing
- [ ] **`test_main_no_transactions_found()`** - Test behavior when no transactions are returned
- [ ] **`test_main_api_key_missing()`** - Test error handling for missing API key
- [ ] **`test_main_api_error_handling()`** - Test handling of API errors
- [ ] **`test_main_file_write_error()`** - Test handling of file write errors
- [ ] **`test_main_success_flow()`** - Test successful end-to-end execution (mocked)

##### **Integration Tests** (0 current tests) - **MEDIUM PRIORITY**
**Missing:**
- [ ] **`test_end_to_end_conversion()`** - Test full pipeline with mock data
- [ ] **`test_multiple_currencies()`** - Test handling of multiple currencies in one conversion
- [ ] **`test_large_transaction_set()`** - Test performance with large datasets
- [ ] **`test_special_characters_in_data()`** - Test handling of special characters in account names, payees, etc.

##### **Test Priority Summary**
- **High Priority** (Critical for reliability): Main module tests, error handling tests, missing category/account handling
- **Medium Priority** (Important for robustness): Additional PocketSmithClient method tests, integration tests, edge cases
- **Low Priority** (Nice to have): Performance tests, special character handling

**Current Coverage Gaps:**
- **Main CLI module**: 0% test coverage
- **Error handling scenarios**: Missing across all modules  
- **Edge cases**: Missing data, API errors, file system errors

### ✅ Phase 6: Integration & Deployment (PENDING)
- [x] **GitHub Actions CI/CD** - Created `.github/workflows/pr-checks.yml`
- [ ] **Update CI/CD with bean-check** - Add beancount validation to automated checks
- [ ] **Create GitHub issues for major features**
- [ ] **Create pull requests linking to issues**
- [ ] **Request code review from user**
- [ ] **Final integration testing**

## Current Status
**Phases 1-4 Complete** - Basic PocketSmith-to-Beancount converter implemented and tested.

**Phase 5 In Progress** - Addressing critical bugs and implementing missing features:
- ✅ 9 of 10 critical bugs COMPLETED
- ✅ 1 of 6 missing features COMPLETED  
- Unit tests needed for all changes
- bean-check validation integration required

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
│   ├── test_pocketsmith_client.py ✅ (4 tests)
│   ├── test_beancount_converter.py ✅ (6 tests)
│   └── test_file_writer.py      ✅ (6 tests)
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
- ✅ Basic test suite (16 tests passing)
- ✅ GitHub Actions CI/CD pipeline
- ✅ Multi-currency support (needs capitalization fix)
- ✅ Account name sanitization and mapping
- ✅ End-to-end workflow tested with real data

### 🐛 Known Issues
- ✅ Commodities use lowercase instead of uppercase (aud → AUD) - FIXED
- ✅ Account directives show "Unknown account" instead of PocketSmith names - FIXED
- ✅ Missing account directives for PocketSmith categories - FIXED
- ✅ Same string used for both payee and narration - FIXED
- ❌ No bean-check validation in CI/CD

### 🚧 Missing Features
- ❌ Pagination for large transaction sets
- ✅ PocketSmith IDs as beancount metadata - IMPLEMENTED
- ❌ Transaction labels as beancount tags
- ❌ needs_review flag support
- ❌ Complete transaction fetching
- ❌ Balance directives

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
uv run bean-check output/*.beancount   # Validate beancount files (after implementing)
```