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
- [ ] **Fix commodities capitalization** - Use AUD, IDR, EUR instead of lowercase
- [ ] **Fix account directives** - Use PocketSmith account names with IDs as metadata instead of "Unknown account"
- [ ] **Add category account directives** - Create account directives for each PocketSmith category
- [ ] **Fix payee/narration mapping** - Use PocketSmith Merchant as payee, Note as narration
- [ ] **Add bean-check validation** - Integrate bean-check into pre-commit hook and GitHub workflow

#### ✨ Missing Features to Implement
- [ ] **Implement pagination** - Fetch transactions using pagination (1,000 per page) with Links header navigation
- [ ] **Add PocketSmith metadata** - Include PocketSmith IDs as beancount metadata for accounts and categories
- [ ] **Convert labels to tags** - Use PocketSmith transaction labels as beancount #tags
- [ ] **Add needs_review flag** - Use PocketSmith needs_review field to add ! flag to transactions
- [ ] **Fetch all transactions** - Ensure complete transaction retrieval (not just subset)
- [ ] **Add balance directives** - Fetch and include balance directives from PocketSmith

#### 🧪 Testing Requirements
- [ ] **Write unit tests for bug fixes** - Comprehensive test coverage for all bug fixes
- [ ] **Write unit tests for new features** - Test coverage for all new functionality

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
- 5 critical bugs identified requiring fixes
- 6 missing features to implement for complete functionality
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
- **Dev**: `ruff`, `pytest`

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
- ❌ Commodities use lowercase instead of uppercase (aud → AUD)
- ❌ Account directives show "Unknown account" instead of PocketSmith names
- ❌ Missing account directives for PocketSmith categories
- ❌ Same string used for both payee and narration
- ❌ No bean-check validation in CI/CD

### 🚧 Missing Features
- ❌ Pagination for large transaction sets
- ❌ PocketSmith IDs as beancount metadata
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