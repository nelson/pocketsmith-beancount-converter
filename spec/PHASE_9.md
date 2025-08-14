# Phase 9 - Improved CLI with Clone, Pull, and Diff Commands ✅ COMPLETED

## Overview

Phase 9 focuses on improving the CLI to have a well-defined list of commands and sub-commands with proper flags and options. This phase introduces `typer` as the CLI framework and implements three new commands: `clone` for initial data download, `pull` for incremental updates with intelligent synchronization using field resolver strategies, and `diff` for comparing local and remote data.

## Goals (ALL ACHIEVED)

- ✅ Replace argparse with typer for better CLI experience
- ✅ Implement a new `clone` command for initial ledger creation with changelog
- ✅ Implement a new `pull` command with field resolver strategies and verbose mode
- ✅ Implement a new `diff` command for comparing local and remote data
- ✅ Add default file detection for all commands
- ✅ Add comprehensive changelog system with UPDATE entries
- ✅ Reorganize CLI code into modular structure
- ✅ Add comprehensive CLI testing (100+ tests)
- ✅ Maintain backward compatibility with existing commands

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

### 3. Pull Command Implementation ✅ ENHANCED

The `pull` command updates an existing ledger with recent PocketSmith data using intelligent synchronization with field resolver strategies:

```bash
peabody pull [-n | --dry-run] [-v | --verbose] [-q | --quiet] [--from <date>] [--to <date>] [--this-month] [--last-month] [--this-year] [--last-year] [<file_or_directory>]
```

#### Core Features

**Default File Detection:**
- If no destination provided, auto-detects main.beancount or .beancount with matching .log file
- Simplifies common workflows by finding the appropriate ledger automatically

**Field Resolver Strategies:**
- Uses intelligent field resolution instead of naive overwrite
- Different strategies for different field types (amounts, notes, categories, tags)
- Preserves user modifications where appropriate

**Incremental Updates:**
- Uses `updated_since` API parameter based on last CLONE or PULL timestamp
- Fetches only transactions modified since last sync for efficiency
- Supports both single-file and hierarchical ledger formats

**Change Tracking:**
- Generates UPDATE changelog entries instead of OVERWRITE
- Shows field-level changes with old → new value format
- Verbose mode (`-v`) prints UPDATE entries to terminal during operation

**Date Range Expansion:**
- Optional date parameters trigger second fetch with new date ranges
- Expands sync scope when new date ranges are specified
- Updates changelog with new date ranges for future syncs

**Output Control:**
- `-n, --dry-run`: Preview changes without modifying files
- `-v, --verbose`: Show UPDATE entries during operation
- `-n -v`: Combine for detailed preview of changes
- `-q, --quiet`: Suppress informational output
- Detailed summary showing update counts and date ranges

**Validation:**
- Requires existing destination with valid changelog
- Must have previous CLONE or PULL entry for sync baseline
- Validates destination format (single-file vs hierarchical)

### 4. Diff Command Implementation ✅ NEW

The `diff` command compares local ledger with remote PocketSmith data without making any modifications:

```bash
peabody diff [--format {summary, ids, changelog, diff}] [--from <date>] [--to <date>] [--this-month] [--last-month] [--this-year] [--last-year] [<file_or_directory>]
```

#### Core Features

**Default File Detection:**
- If no destination provided, auto-detects main.beancount or .beancount with matching .log file
- Consistent with clone and pull commands for seamless workflow

**Multiple Output Formats:**
- `summary` (default): Tally of fetched, different, identical, and not-fetched transactions
- `ids`: List of transaction IDs that differ between local and remote
- `changelog`: DIFF entries showing field-level differences
- `diff`: Traditional diff-style output with local/remote comparison

**Comparison Logic:**
- Fetches transactions without `updated_since` to get complete data
- Compares each field (amount, payee, category, labels, note, merchant)
- Detects differences without modifying any files
- Uses date range from last CLONE/PULL if no dates specified

**Date Range Options:**
- Same date options as clone and pull commands
- Allows focusing comparison on specific time periods
- Uses most recent sync dates as default

**Read-Only Operation:**
- Never modifies local ledger, changelog, or remote data
- Safe to run at any time for status checking
- Useful for understanding what pull would change

**Use Cases:**
- Preview what would change if push command were issued
- Understand local modifications before syncing
- Verify data consistency between local and remote
- Debug synchronization issues

### 5. Changelog System Implementation ✅ ENHANCED

#### Changelog Format
```
[YYYY-MM-DD HH:MM:SS] CLONE [FROM] [TO]
[YYYY-MM-DD HH:MM:SS] PULL [SINCE] [FROM] [TO]  
[YYYY-MM-DD HH:MM:SS] UPDATE [transaction_id] [KEY] [OLD_VALUE] → [NEW_VALUE]
[YYYY-MM-DD HH:MM:SS] DIFF [transaction_id] [KEY] [LOCAL_VALUE] <> [REMOTE_VALUE]
```

#### Changelog Features
- Automatic generation for clone and pull operations
- Change tracking with UPDATE entries for field resolver strategy results
- DIFF entries for comparison operations (not written to file, only displayed)
- Timestamp-based sync coordination using last CLONE/PULL entry
- Support for both single-file and hierarchical modes
- Verbose mode shows UPDATE entries during pull operations

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

## Completion Status ✅ PHASE 9 COMPLETED

### Implemented Features

#### CLI Framework Migration ✅
- ✅ Added typer dependency
- ✅ Created modular CLI structure in `src/cli/`
- ✅ Updated `main.py` as primary entry point with typer app
- ✅ Maintained backward compatibility with existing commands

#### Clone Command ✅
- ✅ Implemented complete clone command with comprehensive options
- ✅ Default file detection for automatic ledger discovery
- ✅ Changelog generation with CLONE entries and date tracking
- ✅ Single-file and hierarchical output modes
- ✅ Quiet mode for suppressed output
- ✅ Date range validation and convenience options
- ✅ Summary output with transaction counts

#### Pull Command ✅ ENHANCED
- ✅ Implemented pull command for incremental updates
- ✅ Field resolver strategies instead of naive overwrite
- ✅ Default file detection for seamless workflow
- ✅ Verbose mode (-v) shows UPDATE entries during operation
- ✅ UPDATE changelog entries with field-level changes
- ✅ Intelligent sync using `updated_since` API parameter
- ✅ Dry-run mode with verbose for detailed preview
- ✅ Date range expansion capabilities
- ✅ Support for both output formats

#### Diff Command ✅ NEW
- ✅ Implemented diff command for comparing local and remote data
- ✅ Multiple output formats (summary, ids, changelog, diff)
- ✅ Default file detection consistent with other commands
- ✅ Read-only operation that never modifies files
- ✅ Date range options matching clone and pull
- ✅ Comprehensive comparison logic for all transaction fields
- ✅ Useful for understanding changes before sync

#### Changelog System ✅ ENHANCED
- ✅ Comprehensive changelog manager with CLONE, PULL, UPDATE, and DIFF entries
- ✅ UPDATE entries replace OVERWRITE for field resolver results
- ✅ Verbose mode integration for real-time change tracking
- ✅ Timestamp-based sync coordination
- ✅ Automatic changelog path determination for both modes
- ✅ Change tracking with old → new value format

#### Testing ✅
- ✅ Complete test suite for clone command (25+ tests)
- ✅ Complete test suite for pull command (20+ tests)
- ✅ Complete test suite for diff command (25+ tests)
- ✅ Comprehensive changelog system tests (10+ tests)
- ✅ CLI validation and error handling tests (18+ tests)
- ✅ Date parsing and file handling tests (35+ tests)
- ✅ Total: 100+ new CLI tests

#### Documentation ✅
- ✅ Updated README with clone, pull, and diff command examples
- ✅ Updated TODO.md marking Phase 9 as complete
- ✅ Updated TESTING.md with comprehensive test plan
- ✅ Complete PHASE_9.md documentation with all features

### Key Achievements

1. **Modern CLI Experience**: Replaced argparse with typer for better UX
2. **Intelligent Synchronization**: Field resolver strategies preserve user modifications
3. **Default File Detection**: Auto-discovers local beancount files for all commands
4. **Comprehensive Comparison**: Diff command provides multiple analysis formats
5. **Enhanced Feedback**: Verbose mode provides real-time update tracking
6. **Audit Trail**: UPDATE entries track field-level changes with full history
7. **Flexible Output**: Support for both single-file and hierarchical structures
8. **Robust Validation**: Comprehensive input validation and error handling
9. **Extensive Testing**: 100+ new tests for CLI functionality

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

## Phase 9.5: CLI Enhancements & Rule System Improvements ✅ COMPLETED

### Overview

Following the completion of Phase 9, additional enhancements were made to improve the CLI user experience and extend the rule system with metadata support and new rule management commands.

### Implemented Features

#### CLI Addendum ✅
- ✅ **Hidden convenience date options**: All date convenience options (`--this-month`, `--last-month`, etc.) are now hidden from help text to reduce clutter
- ✅ **Refactored duplicate code**: Created shared `DateOptions` class and common utilities to eliminate code duplication across commands
- ✅ **Help command**: Added dedicated `help` command that lists all available subcommands with descriptions
- ✅ **Transaction targeting**: Added `--id ID` option to `pull`, `push`, and `diff` commands for targeting specific transactions

#### Rule System Enhancements ✅

**Metadata Fields Support:**
- ✅ Rule preconditions now support metadata fields as a submapping under the `if` mapping
- ✅ Metadata matching uses regex patterns just like other precondition fields
- ✅ Example: `metadata: { needs_reimburse: "true", reimbursed_by: ".*" }`

**Enhanced Logging:**
- ✅ Changed rule matching log keyword from `MATCH` to `APPLY` for consistency
- ✅ All rule application logs now use the `APPLY` keyword

**Rule Management Commands:**
- ✅ `rule add` command with `--if` and `--then` options for creating rules from CLI
- ✅ `rule rm` command that disables rules by adding `disabled: true` flag
- ✅ `rule apply` command with `--dry-run` option for testing specific rule on specific transaction
- ✅ Automatic rule ID assignment and `.rules` file management

### Technical Implementation

#### CLI Architecture Improvements
```python
# Shared date options class
class DateOptions:
    def __init__(self, from_date=None, to_date=None, this_month=False, ...):
        # Centralized date option handling

# Common utilities
def handle_default_destination(destination):
    # Shared destination handling logic

def transaction_id_option():
    # Reusable --id option
```

#### Rule System Extensions
```yaml
# Enhanced rule format with metadata support
- id: 68
  if:
   - metadata:
      - needs_reimburse: true
      - reimbursed_by: ".*"
  then:
    - labels: reimbursed
```

#### Rule Management CLI
```bash
# Add new rules from command line
peabody rule add --if merchant=starbucks --then category=Dining --then labels=coffee

# Remove rules (mark as disabled)
peabody rule rm 68

# Apply specific rule to specific transaction
peabody rule apply 68 123456 --dry-run
```

### Key Benefits

1. **Cleaner CLI Help**: Hidden date options reduce visual clutter while maintaining functionality
2. **Reduced Code Duplication**: Shared utilities eliminate maintenance burden
3. **Enhanced Rule Matching**: Metadata support enables more sophisticated transaction categorization
4. **Command-line Rule Management**: No need to manually edit YAML files
5. **Targeted Operations**: `--id` option allows precise transaction operations
6. **Non-destructive Rule Removal**: Disabled rules preserve audit trail

### Updated File Structure

```
src/cli/
├── common.py              # Shared CLI utilities
├── date_options.py        # Centralized date option handling
├── rule_commands.py       # Rule management commands
├── clone.py              # Enhanced with shared utilities
├── pull.py               # Enhanced with --id option
└── diff.py               # Enhanced with --id option

src/pocketsmith_beancount/
├── rule_models.py        # Enhanced with metadata support
├── rule_loader.py        # Enhanced with disabled rule support
├── rule_matcher.py       # Enhanced with metadata matching
├── rule_transformer.py   # Enhanced with APPLY logging
└── pocketsmith_client.py # Enhanced with get_transaction method
```

## Future Enhancements

### Phase 9.6: Advanced Rule Features
- Rule inheritance and composition
- Conditional rule application
- Rule testing and validation tools

### Phase 9.7: Enhanced CLI Features
- Shell completion support
- Configuration file support
- Interactive mode for complex operations

### Phase 9.8: Advanced CLI Features
- Progress bars for long operations
- Colored output and better formatting
- Plugin system for custom commands

### Phase 9.9: Integration Improvements
- Better integration with existing sync/rules system
- Unified configuration management
- Enhanced logging and debugging options