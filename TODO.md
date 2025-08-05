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

### 🔄 Phase 2: Repository & Authentication (IN PROGRESS)
- [ ] **Create GitHub repository** - Requires user to be logged into GitHub
- [ ] **Get PocketSmith API key** - User needs to obtain from PocketSmith Settings → Developer

### 📋 Phase 3: Core Development (PENDING)
- [ ] **Generate core code to pull PocketSmith transactions**
  - Create `src/pocketsmith_beancount/pocketsmith_client.py`
  - Implement API client with authentication
  - Add transaction fetching functionality
- [ ] **Generate code to convert transactions to beancount format**
  - Create `src/pocketsmith_beancount/beancount_converter.py`
  - Implement transaction mapping logic
  - Handle account mapping and categorization
- [ ] **Generate code to write beancount data locally**
  - Create `src/pocketsmith_beancount/file_writer.py`
  - Implement local file writing with proper formatting
  - Add CLI interface in `src/pocketsmith_beancount/main.py`

### 🧪 Phase 4: Quality Assurance (PENDING)
- [ ] **Lint and format code with ruff**
  - Run `uv run ruff check .`
  - Run `uv run ruff format .`
  - Fix any linting issues
- [ ] **Write unit tests with pytest**
  - Create `tests/test_pocketsmith_client.py`
  - Create `tests/test_beancount_converter.py`
  - Create `tests/test_file_writer.py`
  - Ensure good test coverage

### 🚀 Phase 5: Integration & Deployment (PENDING)
- [ ] **Create GitHub issues for major features**
- [ ] **Create pull requests linking to issues**
- [ ] **Request code review from user**
- [ ] **Final integration testing**

## Current Status
**Phase 1 Complete** - Project initialized with all dependencies and basic structure.

**Next Actions Needed:**
1. User needs to log into GitHub for repository creation
2. User needs to obtain PocketSmith API key from their account settings

## Project Structure (Planned)
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
├── README.md
└── TODO.md (this file)
```

## Dependencies Added
- **Main**: `pocketsmith-api`, `beancount`
- **Dev**: `ruff`, `pytest`

## Notes
- Using uv for Python package management
- Following AGENTS.md format for documentation
- Will create GitHub issues and PRs for code review process
- API key will be configured via environment variables for security