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

#### 🧪 Testing Requirements
- [x] **Write unit tests for bug fixes** - Comprehensive test coverage for all bug fixes ✅ COMPLETED
- [x] **Write unit tests for new features** - Test coverage for all new functionality ✅ COMPLETED

#### ✅ Unit Tests Analysis (Current: 79 tests - Target Exceeded!) - **COMPLETED**

##### **PocketSmithClient Tests** (10 → 18 total tests) ✅ COMPLETED
**Existing Tests (10):**
- [x] **`test_get_accounts()`** - Test fetching user accounts ✅ COMPLETED
- [x] **`test_get_categories()`** - Test fetching user categories ✅ COMPLETED
- [x] **`test_get_transaction_accounts()`** - Test fetching transaction accounts ✅ COMPLETED
- [x] **`test_make_request_error_handling()`** - Test HTTP error handling (404, 401, 500) ✅ COMPLETED
- [x] **`test_get_transactions_without_params()`** - Test transactions without date/account filters ✅ COMPLETED
- [x] **`test_api_response_type_handling()`** - Test handling of non-list responses from API ✅ COMPLETED

**New Phase 5 Tests (8 additional):**
- [x] **`test_parse_link_header_valid()`** - Test parsing valid Link headers with next/prev/first/last relations ✅ COMPLETED
- [x] **`test_parse_link_header_empty()`** - Test handling empty/None Link headers ✅ COMPLETED
- [x] **`test_parse_link_header_malformed()`** - Test handling malformed Link headers ✅ COMPLETED
- [x] **`test_get_transactions_pagination()`** - Test pagination flow with multiple pages ✅ COMPLETED
- [x] **`test_get_transactions_pagination_no_next()`** - Test single page response (no pagination) ✅ COMPLETED
- [x] **`test_get_account_balances_success()`** - Test successful balance fetching ✅ COMPLETED
- [x] **`test_get_account_balances_empty()`** - Test when no balances are returned ✅ COMPLETED
- [x] **`test_get_account_balances_error()`** - Test API error handling for balance requests ✅ COMPLETED

##### **BeancountConverter Tests** (23 → 35 total tests) ✅ COMPLETED
**Existing Tests (23):**
- [x] **`test_get_category_account_transfer()`** - Test transfer category handling ✅ COMPLETED
- [x] **`test_get_category_account_none()`** - Test null/missing category handling ✅ COMPLETED
- [x] **`test_get_account_name_credit_card()`** - Test credit card account type mapping to Liabilities ✅ COMPLETED
- [x] **`test_get_account_name_loan()`** - Test loan account type mapping to Liabilities ✅ COMPLETED
- [x] **`test_get_account_name_missing_institution()`** - Test accounts without institution data ✅ COMPLETED
- [x] **`test_convert_transaction_missing_category()`** - Test transactions without categories ✅ COMPLETED
- [x] **`test_convert_transaction_missing_transaction_account()`** - Test transactions without account data ✅ COMPLETED
- [x] **`test_convert_transaction_quote_escaping()`** - Test payee/narration with quotes ✅ COMPLETED
- [x] **`test_convert_transactions_full_integration()`** - Test the full `convert_transactions()` method ✅ COMPLETED
- [x] **`test_generate_account_declarations_missing_dates()`** - Test accounts without starting_balance_date ✅ COMPLETED
- [x] **`test_generate_commodity_declarations_empty()`** - Test when no currencies are tracked ✅ COMPLETED

**New Phase 5 Tests (12 additional):**
- [x] **`test_convert_transaction_with_labels()`** - Test labels converted to tags ✅ COMPLETED
- [x] **`test_convert_transaction_with_empty_labels()`** - Test empty labels array ✅ COMPLETED
- [x] **`test_convert_transaction_with_special_char_labels()`** - Test label sanitization ✅ COMPLETED
- [x] **`test_convert_transaction_needs_review_true()`** - Test ! flag for needs_review=true ✅ COMPLETED
- [x] **`test_convert_transaction_needs_review_false()`** - Test * flag for needs_review=false ✅ COMPLETED
- [x] **`test_convert_transaction_needs_review_missing()`** - Test default * flag when field missing ✅ COMPLETED
- [x] **`test_convert_transaction_labels_and_needs_review()`** - Test both features together ✅ COMPLETED
- [x] **`test_generate_balance_directives_success()`** - Test balance directive generation ✅ COMPLETED
- [x] **`test_generate_balance_directives_empty()`** - Test with no balance data ✅ COMPLETED
- [x] **`test_generate_balance_directives_missing_account()`** - Test with invalid account IDs ✅ COMPLETED
- [x] **`test_convert_transactions_with_balance_directives()`** - Test integration with balance directives ✅ COMPLETED
- [x] **`test_convert_transactions_without_balance_directives()`** - Test backward compatibility ✅ COMPLETED

##### **BeancountFileWriter Tests** (10 total tests) ✅ COMPLETED
**Implemented:**
- [x] **`test_init_with_env_var()`** - Test initialization with BEANCOUNT_OUTPUT_DIR environment variable ✅ COMPLETED
- [x] **`test_write_file_creates_directory()`** - Test that output directory is created if it doesn't exist ✅ COMPLETED
- [x] **`test_write_file_with_extension_already_present()`** - Test filename handling when .beancount extension already exists ✅ COMPLETED
- [x] **`test_append_to_nonexistent_file()`** - Test appending to a file that doesn't exist yet ✅ COMPLETED

##### **Main Module Tests** (6 → 9 total tests) ✅ COMPLETED - **HIGH PRIORITY**
**Existing Tests (6):**
- [x] **`test_main_argument_parsing()`** - Test CLI argument parsing ✅ COMPLETED
- [x] **`test_main_no_transactions_found()`** - Test behavior when no transactions are returned ✅ COMPLETED
- [x] **`test_main_api_key_missing()`** - Test error handling for missing API key ✅ COMPLETED
- [x] **`test_main_api_error_handling()`** - Test handling of API errors ✅ COMPLETED
- [x] **`test_main_file_write_error()`** - Test handling of file write errors ✅ COMPLETED
- [x] **`test_main_success_flow()`** - Test successful end-to-end execution (mocked) ✅ COMPLETED

**New Phase 5 Tests (3 additional):**
- [x] **`test_main_with_balance_fetching()`** - Test successful balance fetching in main flow ✅ COMPLETED
- [x] **`test_main_balance_fetch_error()`** - Test handling of balance fetch errors ✅ COMPLETED
- [x] **`test_main_balance_fetch_partial_failure()`** - Test when some accounts fail balance fetch ✅ COMPLETED

##### **Integration Tests** (4 → 7 total tests) ✅ COMPLETED - **MEDIUM PRIORITY**
**Existing Tests (4):**
- [x] **`test_end_to_end_conversion()`** - Test full pipeline with mock data ✅ COMPLETED
- [x] **`test_multiple_currencies()`** - Test handling of multiple currencies in one conversion ✅ COMPLETED
- [x] **`test_large_transaction_set()`** - Test performance with large datasets ✅ COMPLETED
- [x] **`test_special_characters_in_data()`** - Test handling of special characters in account names, payees, etc. ✅ COMPLETED

**New Phase 5 Tests (3 additional):**
- [x] **`test_end_to_end_with_labels_and_flags()`** - Test full pipeline with labels and needs_review ✅ COMPLETED
- [x] **`test_end_to_end_with_balance_directives()`** - Test full pipeline with balance directives ✅ COMPLETED
- [x] **`test_pagination_integration()`** - Test pagination in full pipeline ✅ COMPLETED

##### ✅ **Test Coverage Summary** - **COMPLETED**
- **High Priority** (Critical for reliability): ✅ All Phase 5 features fully tested - Pagination, labels/tags, needs_review flags
- **Medium Priority** (Important for robustness): ✅ Balance directives, error handling for new features
- **Low Priority** (Nice to have): ✅ All completed - Performance tests, special character handling

**✅ Coverage Achievements:**
- **Phase 5 Features**: ✅ Comprehensive test coverage for all new functionality
- **Pagination**: ✅ Link header parsing, multi-page fetching, error handling
- **Labels & Tags**: ✅ Label sanitization, tag conversion, edge cases
- **Needs Review Flags**: ✅ Flag handling, missing field defaults
- **Balance Directives**: ✅ Balance fetching, directive generation, integration
- **Error Scenarios**: ✅ API errors for new endpoints, partial failures
- **Integration**: ✅ End-to-end testing with all new features combined

**Final Coverage Achievements:**
- **Total Tests**: 53 → 79 tests (49% increase - Target exceeded!)
- **PocketSmithClient**: 10 → 18 tests (80% increase for new pagination/balance features)
- **BeancountConverter**: 23 → 35 tests (52% increase for labels/tags/balance features)
- **Main Module**: 6 → 9 tests (50% increase for balance fetching logic)
- **Integration**: 4 → 7 tests (75% increase for Phase 5 feature integration)

### ✅ Phase 6: Integration & Deployment (PENDING)
- [x] **GitHub Actions CI/CD** - Created `.github/workflows/pr-checks.yml`
- [ ] **Update CI/CD with bean-check** - Add beancount validation to automated checks
- [ ] **Create GitHub issues for major features**
- [ ] **Create pull requests linking to issues**
- [ ] **Request code review from user**
- [ ] **Final integration testing**

## Current Status
**Phases 1-5 Complete** - PocketSmith-to-Beancount converter fully implemented with comprehensive test coverage.

**✅ Phase 5 COMPLETED** - All critical bugs fixed, all missing features implemented, and comprehensive test suite implemented:
- ✅ **10 of 10 critical bugs COMPLETED**
- ✅ **6 of 6 missing features COMPLETED**  
- ✅ **Comprehensive unit test suite implemented (79 tests total - 49% increase)**
- ✅ **All tests passing with full coverage of edge cases and error scenarios**
- ✅ **Integration tests for end-to-end pipeline validation**
- ✅ **Performance testing with large datasets**
- ✅ **Complete test coverage for all Phase 5 features**
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
uv run bean-check output/*.beancount   # Validate beancount files (after implementing)
```
