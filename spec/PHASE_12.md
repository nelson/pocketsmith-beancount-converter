# PHASE 12: Enhanced Rule Command Features

## Overview

This phase enhances the `rule` command with additional subcommands and modifies the existing `rule apply` behavior to prevent unintended remote data modification.

## Changes Implemented

### 1. Modified `rule apply` Command

**Change**: Removed write-back to remote PocketSmith data from `rule apply`.

**Rationale**: The `rule apply` command should only modify the local beancount ledger. Write-back to remote data should only occur during `pull` or `push` operations to maintain data integrity and provide explicit control over when remote changes occur.

**Implementation**:
- Removed PocketSmith API write-back logic from `rule_apply_command()` in `src/cli/rule_commands.py`
- Added comment explaining that write-back only happens during pull/push commands
- Resolution strategies still support write-back capability for use by pull/push commands

### 2. New `rule list` Command

**Purpose**: List all rules found with optional filtering and detail levels.

**Usage**:
```bash
peabody rule list [--verbose] [--id ID_FILTER] [--rules RULES_PATH]
```

**Features**:
- **Default mode**: Shows summary with rule counts by file and destination category
- **Verbose mode** (`--verbose`): Shows detailed rule information including conditions and transforms
- **ID filtering** (`--id`): Supports single IDs, comma-separated lists, and ranges (e.g., `1,3-5,7-8`)
- **Rules path** (`--rules`): Defaults to `.rules/` directory

**Output Examples**:

*Summary mode*:
```
Found 15 rules
Loaded from 3 files:
  rules.yaml: 8 rules (IDs: 1, 2, 3, 4, 5, 6, 7, 8)
  custom.yaml: 4 rules (IDs: 9, 10, 11, 12)
  auto.yaml: 3 rules (IDs: 13, 14, 15)

Rules by destination category:
  Expenses:Food: 6 rules
  Expenses:Transport: 4 rules
  Income:Salary: 2 rules
  unknown: 3 rules
```

*Verbose mode*:
```
RULES:

RULE 1
  IF:
    MERCHANT: Starbucks.*
  THEN:
    CATEGORY: Expenses:Food:Coffee

RULE 2
  IF:
    MERCHANT: Uber.*
    CATEGORY: Transport
  THEN:
    CATEGORY: Expenses:Transport:Rideshare
    METADATA:
      service: rideshare
```

### 3. New `rule lookup` Command

**Purpose**: Test which rule would match given transaction-like data.

**Usage**:
```bash
peabody rule lookup [--merchant MERCHANT] [--category CATEGORY] [--account ACCOUNT] [--rules RULES_PATH]
```

**Requirements**:
- At least one of `--merchant`, `--category`, or `--account` must be provided
- Searches rules in priority order to find first match
- Shows detailed match information including patterns and resulting transforms

**Output Format**:
```
TRANSACTION LOOKUP_001 matches RULE 5

  MERCHANT Starbucks Coffee #123 ~= Starbucks.*
  CATEGORY Food ~= Food

  CATEGORY Food -> Expenses:Food:Coffee
  LABELS N/A -> coffee,beverage
  METADATA
    NEW vendor_type: coffee_shop
    MOD location: unknown -> store_123
```

**If no match found**:
```
No matching rule found for the given transaction data
```

## Implementation Details

### File Changes

1. **main.py**: Added `rule list` and `rule lookup` command definitions
2. **src/cli/rule_commands.py**: 
   - Modified `rule_apply_command()` to remove PocketSmith write-back
   - Added `rule_list_command()` with summary and verbose modes
   - Added `rule_lookup_command()` with mock transaction matching
   - Added `_parse_rule_ids()` utility for ID range parsing

### New Dependencies

- Leverages existing `RuleLoader`, `RuleMatcher`, and rule infrastructure
- No new external dependencies required

### Error Handling

- Comprehensive validation for command arguments
- Graceful handling of missing rules files
- Clear error messages for invalid ID ranges or missing parameters

## Testing Strategy

### Unit Tests
- Test rule ID parsing with various formats
- Test summary vs verbose output modes
- Test lookup command with different parameter combinations
- Test error conditions (missing files, invalid arguments)

### Integration Tests
- Test with real rule files and directory structures
- Verify rule apply no longer writes back to remote
- Test filtering by ID ranges
- Test lookup against actual rule matching logic

### Manual Testing Scenarios
1. List rules in directory with multiple files
2. Use verbose mode to inspect rule details
3. Filter by various ID patterns
4. Lookup rules with different merchant/category/account combinations
5. Verify rule apply only affects local ledger

## Compatibility

- **Backward Compatible**: Existing `rule add`, `rule rm`, and `rule apply` commands unchanged in interface
- **Resolution Strategy**: Write-back capability preserved in resolution strategies for use by pull/push commands
- **File Formats**: No changes to rule file formats or structures

## Benefits

1. **Enhanced Visibility**: `rule list` provides comprehensive overview of rule organization
2. **Rule Testing**: `rule lookup` enables testing rules without applying them
3. **Data Safety**: `rule apply` no longer accidentally modifies remote data
4. **Operational Control**: Clear separation between local rule application and remote synchronization