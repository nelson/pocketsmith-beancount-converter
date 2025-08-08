# CONTRIBUTING

# Contribution Guidelines

This document outlines the contribution process and development guidelines for the PocketSmith to Beancount Converter project.

## Development Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd vibe-opencode-pocketsmith-beancount
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your PocketSmith API key
   ```

4. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

## Code Quality Standards

### Linting and Formatting
- **Ruff**: Used for both linting and formatting
- **MyPy**: Static type checking with strict mode
- **Pre-commit**: Automated quality checks

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

### Testing Requirements
- **Minimum 85% test coverage** for new code
- **All tests must pass** before merging
- **Property-based testing** with hypothesis for complex logic
- **Real API tests** for endpoint validation (when applicable)

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html --cov-fail-under=85

# Run specific test categories
uv run pytest tests/test_synchronizer.py  # Sync tests
uv run pytest -k "property"              # Property-based tests
uv run pytest -k "real_api"              # Real API tests
```

## Synchronization Development Guidelines

### Field Resolution Strategy Implementation

When implementing new field resolution strategies:

1. **Strategy Definition**: Each field must have exactly one resolution strategy (1-5)
2. **Strategy Implementation**: Implement in `src/pocketsmith_beancount/field_resolver.py`
3. **Test Coverage**: Add comprehensive tests in `tests/test_field_resolver.py`
4. **Documentation**: Update field mapping in README.md

### API Write-back Development

When adding new write-back functionality:

1. **Rate Limiting**: Implement proper rate limiting and backoff
2. **Error Handling**: Handle all API error scenarios gracefully
3. **Dry-run Mode**: Support preview mode for all operations
4. **Validation**: Validate data before sending to API
5. **Logging**: Log all API operations for debugging

### Transaction Comparison Logic

When modifying comparison logic:

1. **Timestamp Accuracy**: Use millisecond precision for change detection
2. **Field-level Granularity**: Detect changes at individual field level
3. **ID Matching**: Always use transaction IDs for pairing
4. **Null Handling**: Handle missing/null values consistently

## Contribution Checklist

This checklist should be followed for every code contribution submitted to GitHub.

### Pre-Development
- [ ] Create GitHub issue describing the feature/bug
- [ ] Review existing code and tests for similar functionality
- [ ] Plan implementation approach and discuss if needed

### Development Process
- [ ] Create well-named feature branch from main
- [ ] Implement functionality following project patterns
- [ ] Add comprehensive unit tests (aim for >90% coverage)
- [ ] Add integration tests for new features
- [ ] Update documentation (README, TODO, TESTING as needed)

### Quality Assurance
- [ ] Run full test suite: `uv run pytest`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Run linting: `uv run ruff check .`
- [ ] Run formatting: `uv run ruff format .`
- [ ] Run pre-commit hooks: `uv run pre-commit run --all-files`
- [ ] Validate beancount output: `uv run bean-check output/main.beancount`

### Synchronization-Specific Checks
- [ ] Test all 5 field resolution strategies if applicable
- [ ] Test API write-back functionality with mocks and real API
- [ ] Verify changelog integration logs all operations
- [ ] Test dry-run mode for preview functionality
- [ ] Validate conflict resolution scenarios

### Submission Process
- [ ] Commit changes with conventional commit format:
  - **First line**: `<type>: #[ISSUE_NUMBER] [SUMMARY]`
    - `<type>` follows [Conventional Commits](https://www.conventionalcommits.org) (feat, fix, docs, etc.)
    - `[ISSUE_NUMBER]` is the GitHub issue number (e.g., #17)
    - `[SUMMARY]` is a concise one-line description
  - **Body**: Detailed description with bullet points of changes
  - **Final line**: `Closes #[ISSUE_NUMBER]`
- [ ] Create GitHub pull request linking to the issue
- [ ] Ensure all CI checks pass
- [ ] Request review from maintainers

### Post-Submission
- [ ] Address review feedback promptly
- [ ] Update tests/docs based on review comments
- [ ] Ensure final CI run passes
- [ ] Monitor for any post-merge issues

## Architecture Guidelines

### Module Organization
- **Single Responsibility**: Each module should have one clear purpose
- **Dependency Injection**: Use dependency injection for testability
- **Error Handling**: Consistent error handling patterns across modules
- **Logging**: Structured logging with appropriate levels

### Synchronization Architecture
- **Modular Design**: Separate concerns into distinct modules
- **Strategy Pattern**: Use strategy pattern for field resolution
- **Observer Pattern**: Use for progress reporting and logging
- **Command Pattern**: Use for API operations with undo capability

### Testing Architecture
- **Test Isolation**: Each test should be independent
- **Mock External Dependencies**: Mock API calls and file operations
- **Property-based Testing**: Use hypothesis for complex scenarios
- **Performance Testing**: Include benchmarks for critical paths

## Common Patterns

### Error Handling
```python
try:
    result = api_operation()
except APIError as e:
    logger.error(f"API operation failed: {e}")
    raise SynchronizationError(f"Failed to sync: {e}") from e
```

### Logging
```python
logger.info("Starting synchronization", extra={
    "transaction_count": len(transactions),
    "operation": "sync"
})
```

### Configuration
```python
@dataclass
class SyncConfig:
    dry_run: bool = False
    batch_size: int = 100
    max_retries: int = 3
```

## Getting Help

- **Documentation**: Check README.md, TODO.md, and TESTING.md
- **Issues**: Search existing GitHub issues
- **Code Examples**: Look at existing tests for usage patterns
- **Architecture**: Review existing modules for design patterns
