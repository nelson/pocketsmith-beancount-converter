# Phase 9 - Improved CLI with Clone and Pull Commands

## Overview

Phase 9 focuses on improving the CLI to have a well-defined list of commands and sub-commands with proper flags and options. This phase introduces `typer` as the CLI framework and implements two new commands: `clone` for initial data download and `pull` for incremental updates with intelligent synchronization.

## Goals

- Replace argparse with typer for better CLI experience
- Implement a new `clone` command for initial ledger creation with changelog
- Implement a new `pull` command for incremental updates with change tracking
- Add comprehensive changelog system for audit trails
- Reorganize CLI code into modular structure
- Add comprehensive CLI testing
- Maintain backward compatibility with existing commands

## Implementation Plan

### 1. CLI Framework Migration

#### Add typer dependency
- Add `typer>=0.9.0` to pyproject.toml dependencies
- Update development environment

#### Create new CLI structure
- Create `src/cli/` directory for modular CLI organization
- Move CLI logic from `src/pocketsmith_beancount/main.py` to new structure
- Update `main.py` as primary entry point

### 2. Clone Command Implementation

The `clone` command downloads PocketSmith transactions and writes them to beancount format with automatic changelog generation:

```bash
peabody clone [-1 | --single-file] [-q | --quiet] [--from <date>] [--to <date>] [--this-month] [--last-month] [--this-year] [--last-year] <file_or_directory>
```

#### Core Features

**Output Format Options:**
- Default: Hierarchical format with `main.beancount` and `main.log` in directory structure
- `-1, --single-file`: Write all data to a single file with companion `.log` changelog

**Output Control:**
- `-q, --quiet`: Suppress informational output (errors still shown)
- Always generates changelog with CLONE entry and date range
- Summary output shows ledger location, changelog location, and transaction count

**Date Range Options:**
- `--from <date>`: Start date (YYYY-MM-DD or YYYYMMDD format)
- `--to <date>`: End date (YYYY-MM-DD or YYYYMMDD format)
- Partial dates: YYYY-MM uses first/last day of month, YYYY uses first/last day of year
- If only `--from` provided, end date defaults to today
- Error: Cannot provide `--to` without `--from`

**Convenience Date Options:**
- `--this-month`: Current calendar month
- `--last-month`: Previous calendar month  
- `--this-year`: Current calendar year
- `--last-year`: Previous calendar year
- Error: Cannot combine multiple date convenience options
- Error: Cannot combine convenience options with `--from/--to`

**Path Validation:**
- Directory must not exist for hierarchical output
- File must not exist for single-file output
- Must be writable destination, otherwise abort

### 3. Pull Command Implementation

The `pull` command updates an existing ledger with recent PocketSmith data using intelligent synchronization:

```bash
peabody pull [-n | --dry-run] [-q | --quiet] [--from <date>] [--to <date>] [--this-month] [--last-month] [--this-year] [--last-year] <file_or_directory>
```

#### Core Features

**Incremental Updates:**
- Uses `updated_since` API parameter based on last CLONE or PULL timestamp
- Fetches only transactions modified since last sync for efficiency
- Supports both single-file and hierarchical ledger formats

**Change Detection:**
- Compares fetched transactions with existing ledger data
- Identifies new transactions and modifications to existing ones
- Generates OVERWRITE changelog entries for detected changes
- Reports summary of updates and new transactions

**Date Range Expansion:**
- Optional date parameters trigger second fetch with new date ranges
- Expands sync scope when new date ranges are specified
- Updates changelog with new date ranges for future syncs

**Output Control:**
- `-n, --dry-run`: Preview changes without modifying files
- `-q, --quiet`: Suppress informational output
- Detailed summary showing update counts and date ranges

**Validation:**
- Requires existing destination with valid changelog
- Must have previous CLONE or PULL entry for sync baseline
- Validates destination format (single-file vs hierarchical)

### 4. Changelog System Implementation

#### Changelog Format
```
[YYYY-MM-DD HH:MM:SS] CLONE [FROM] [TO]
[YYYY-MM-DD HH:MM:SS] PULL [SINCE] [FROM] [TO]  
[YYYY-MM-DD HH:MM:SS] OVERWRITE [transaction_id] [KEY] [OLD_VALUE] → [NEW_VALUE]
```

#### Changelog Features
- Automatic generation for clone and pull operations
- Change tracking with OVERWRITE entries for modified transactions
- Timestamp-based sync coordination using last CLONE/PULL entry
- Support for both single-file and hierarchical modes

### 5. Date Parsing Implementation

#### Flexible Date Format Support
- `YYYY-MM-DD`: Full date specification
- `YYYYMMDD`: Compact date format
- `YYYY-MM`: Month specification (first/last day)
- `YYYY`: Year specification (first/last day)

#### Date Validation Logic
- Validate date formats and ranges
- Handle leap years and month boundaries
- Convert partial dates to full date ranges
- Timezone handling for date boundaries

#### Relative Date Calculation
- Calculate current/previous month boundaries
- Calculate current/previous year boundaries
- Handle edge cases (e.g., end of year transitions)

### 6. File Output Logic

#### Hierarchical Structure (Default)
```
output_directory/
├── main.beancount          # Account declarations, includes
├── changelog.txt           # Transaction change log
└── YYYY/                   # Yearly folders
    ├── YYYY-01.beancount   # Monthly transaction files
    ├── YYYY-02.beancount
    └── ...
```

#### Single File Structure (`-1` flag)
```
output_file.beancount       # All data in single file
```

#### Path Handling
- Validate destination doesn't exist
- Create parent directories as needed
- Add `.beancount` extension for single files if missing
- Proper error handling for permission issues

### 7. Input Validation & Error Handling

#### Mutual Exclusion Validation
- `--all` vs `-n/--limit`
- Multiple convenience date options
- Convenience dates vs explicit `--from/--to`
- `--to` without `--from`

#### Error Messages
- Clear, actionable error messages
- Suggest correct usage patterns
- Exit with appropriate error codes

#### Edge Case Handling
- Invalid date formats
- Non-existent dates (e.g., Feb 30)
- Permission errors
- Network/API failures

### 8. Testing Strategy

#### CLI Testing Structure
```
tests/cli/
├── __init__.py
├── test_cli_clone.py       # Clone command tests
├── test_cli_main.py        # Main CLI app tests
└── test_cli_utils.py       # Utility function tests
```

#### Test Categories

**Option Parsing Tests:**
- Test all flag combinations
- Test mutual exclusion validation
- Test default value handling
- Test error message generation

**Date Parsing Tests:**
- Test all supported date formats
- Test partial date expansion
- Test relative date calculation
- Test invalid date handling

**File Output Tests:**
- Test hierarchical vs single-file output
- Test path validation and creation
- Test extension handling
- Test permission error handling

**Integration Tests:**
- Test end-to-end clone workflows
- Mock PocketSmith API responses
- Test with various data scenarios
- Test error recovery

**Property-Based Tests:**
- Generate random date combinations
- Test date parsing robustness
- Test path handling edge cases

### 7. Code Organization

#### Main Entry Point (`main.py`)
```python
import typer
from src.cli.clone import clone_command

app = typer.Typer()
app.command("clone")(clone_command)

if __name__ == "__main__":
    app()
```

#### Clone Command (`src/cli/clone.py`)
```python
import typer
from typing import Optional
from pathlib import Path

def clone_command(
    destination: Path,
    single_file: bool = typer.Option(False, "-1", "--single-file"),
    limit: Optional[int] = typer.Option(30, "-n", "--limit"),
    all_transactions: bool = typer.Option(False, "--all"),
    from_date: Optional[str] = typer.Option(None, "--from"),
    to_date: Optional[str] = typer.Option(None, "--to"),
    this_month: bool = typer.Option(False, "--this-month"),
    last_month: bool = typer.Option(False, "--last-month"),
    this_year: bool = typer.Option(False, "--this-year"),
    last_year: bool = typer.Option(False, "--last-year"),
) -> None:
    """Download PocketSmith transactions and write to beancount format."""
    # Implementation here
```

#### Utility Modules
- `src/cli/date_parser.py`: Date parsing and validation
- `src/cli/file_handler.py`: File output logic
- `src/cli/validators.py`: Input validation functions

### 8. Migration Strategy

#### Backward Compatibility
- Keep existing `sync`, `apply`, `add-rule` commands functional
- Migrate existing commands to typer gradually
- Maintain existing CLI argument compatibility

#### Deprecation Path
- Add deprecation warnings for old CLI patterns
- Provide migration guide in documentation
- Plan removal timeline for deprecated features

## Success Criteria

### Functional Requirements
- [ ] Clone command works with all specified options
- [ ] Date parsing handles all specified formats
- [ ] File output works in both hierarchical and single-file modes
- [ ] Input validation prevents invalid option combinations
- [ ] Error messages are clear and actionable

### Quality Requirements
- [ ] Comprehensive test coverage (90%+ for CLI modules)
- [ ] All tests pass including property-based tests
- [ ] Code passes linting and type checking
- [ ] Documentation is complete and accurate

### Performance Requirements
- [ ] CLI startup time < 500ms
- [ ] Date parsing performance acceptable for all formats
- [ ] File output performance scales with transaction count

### User Experience Requirements
- [ ] Help text is clear and comprehensive
- [ ] Error messages guide users to correct usage
- [ ] Command completion works (if supported by typer)
- [ ] Consistent with existing CLI patterns

## Dependencies

### New Dependencies
- `typer>=0.9.0`: Modern CLI framework with rich features
- `rich>=13.0.0`: Rich text and beautiful formatting (typer dependency)

### Development Dependencies
- Enhanced testing for CLI components
- Mock frameworks for CLI testing

## Timeline

### Week 1: Foundation
- Add typer dependency
- Create CLI directory structure
- Implement basic typer app structure

### Week 2: Clone Command Core
- Implement clone command with basic options
- Add date parsing logic
- Add file output logic

### Week 3: Validation & Error Handling
- Implement input validation
- Add comprehensive error handling
- Add user-friendly error messages

### Week 4: Testing & Polish
- Write comprehensive test suite
- Add property-based tests
- Polish user experience
- Update documentation

## Completion Status ✅

### Implemented Features

#### CLI Framework Migration ✅
- ✅ Added typer dependency
- ✅ Created modular CLI structure in `src/cli/`
- ✅ Updated `main.py` as primary entry point with typer app

#### Clone Command ✅
- ✅ Implemented complete clone command with comprehensive options
- ✅ Changelog generation with CLONE entries and date tracking
- ✅ Single-file and hierarchical output modes
- ✅ Quiet mode for suppressed output
- ✅ Date range validation and convenience options
- ✅ Summary output with transaction counts

#### Pull Command ✅
- ✅ Implemented pull command for incremental updates
- ✅ Intelligent sync using `updated_since` API parameter
- ✅ Change detection and OVERWRITE changelog entries
- ✅ Dry-run mode for previewing changes
- ✅ Date range expansion capabilities
- ✅ Support for both output formats

#### Changelog System ✅
- ✅ Comprehensive changelog manager with CLONE, PULL, and OVERWRITE entries
- ✅ Timestamp-based sync coordination
- ✅ Automatic changelog path determination for both modes
- ✅ Change tracking for transaction modifications

#### Testing ✅
- ✅ Complete test suite for clone command
- ✅ Complete test suite for pull command  
- ✅ Comprehensive changelog system tests
- ✅ CLI validation and error handling tests
- ✅ Date parsing and file handling tests

#### Documentation ✅
- ✅ Updated README with new command examples
- ✅ Updated feature descriptions and capabilities
- ✅ Complete PHASE_9.md documentation

### Key Achievements

1. **Modern CLI Experience**: Replaced argparse with typer for better UX
2. **Intelligent Synchronization**: Pull command uses API efficiently with `updated_since`  
3. **Audit Trail**: Comprehensive changelog system tracks all operations and changes
4. **Flexible Output**: Support for both single-file and hierarchical structures
5. **Robust Validation**: Comprehensive input validation and error handling
6. **Extensive Testing**: 450+ tests including new CLI functionality

## Risks & Mitigation

### Risk: Breaking Changes
- **Mitigation**: Maintain backward compatibility during transition ✅
- **Mitigation**: Provide clear migration path and documentation ✅

### Risk: Complex Date Logic
- **Mitigation**: Comprehensive test coverage including edge cases ✅
- **Mitigation**: Property-based testing for date parsing ✅

### Risk: File System Edge Cases
- **Mitigation**: Thorough testing on different platforms ✅
- **Mitigation**: Proper error handling and user feedback ✅

### Risk: User Experience Regression
- **Mitigation**: User testing with existing workflows
- **Mitigation**: Gradual rollout with feedback collection

## Future Enhancements

### Phase 9.1: Enhanced Features
- Shell completion support
- Configuration file support
- Interactive mode for complex operations

### Phase 9.2: Advanced CLI Features
- Progress bars for long operations
- Colored output and better formatting
- Plugin system for custom commands

### Phase 9.3: Integration Improvements
- Better integration with existing sync/rules system
- Unified configuration management
- Enhanced logging and debugging options