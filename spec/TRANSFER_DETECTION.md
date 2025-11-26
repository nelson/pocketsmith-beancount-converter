# Transfer Detection Implementation - Final Summary

## Complete Feature Overview

A comprehensive system for automatically detecting and managing transfer transactions between accounts, with bidirectional sync to PocketSmith.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Transfer Detection System                 │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼──────┐
    │ Detection │      │  Application │      │    Sync    │
    │  Engine   │      │    Layer     │      │   Layer    │
    └────┬─────┘      └──────┬──────┘      └─────┬──────┘
         │                    │                    │
    ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼──────┐
    │ Spatial  │      │  Metadata   │      │ PocketSmith│
    │  Hash    │      │  Applier    │      │  Encoding  │
    │  Index   │      │             │      │            │
    └──────────┘      └─────────────┘      └────────────┘
```

---

## Module Structure

```
src/
├── transfers/                          # New module
│   ├── __init__.py
│   ├── models.py                       # TransferPair, DetectionCriteria, DetectionResult
│   ├── detector.py                     # TransferDetector with spatial hash
│   ├── detector_option1_backup.py      # Binary search fallback
│   ├── applier.py                      # TransferApplier for marking transactions
│   └── category_helper.py              # Find Transfer category ID
│
├── pocketsmith/
│   └── metadata_encoding.py            # New: [key:value] encoding in notes
│
├── cli/
│   └── transfer_commands.py            # New: CLI for detect-transfers
│
├── compare/
│   └── model.py                        # Updated: +is_transfer, +paired, +suspect_reason
│
└── beancount/
    ├── write.py                        # Updated: Write transfer metadata
    └── read.py                         # Updated: Read transfer metadata

tests/transfers/                        # New test suite
├── test_detector.py
├── test_detector_performance.py
├── test_applier.py
├── test_metadata_encoding.py
├── test_idempotency.py
└── test_integration.py
```

---

## Data Flow

### Detection Flow
```
1. Read Beancount → Parse Transactions
                          ↓
2. Build Spatial Hash Index (date × amount)
                          ↓
3. For each transaction:
   - Find candidates (same amount ± tolerance, nearby dates)
   - Check criteria (opposite direction, different accounts)
   - Classify as confirmed or suspected
                          ↓
4. Return DetectionResult
   - confirmed_pairs
   - suspected_pairs
   - unmatched_transactions
```

### Application Flow (Confirmed)
```
1. Mark both transactions:
   is_transfer: "true"
   paired: <other_txn_id>
   category: Expenses:Transfer
                          ↓
2. Write to Beancount ledger
                          ↓
3. User runs: push
                          ↓
4. Encode in PocketSmith:
   - is_transfer: true (API field)
   - note: "Original note [paired:12345]"
   - category_id: <Transfer category>
```

### Application Flow (Suspected)
```
1. Mark both transactions:
   paired: <other_txn_id>
   suspect_reason: "date-delay-3days, amount-mismatch-fx"
   (NO is_transfer, NO category change)
                          ↓
2. Write to Beancount:
   - Metadata: suspect_reason: "..."
   - Comment: ; Suspected transfer: ...
                          ↓
3. User runs: push
                          ↓
4. Encode in PocketSmith:
   - note: "... [paired:12345] [suspect_reason:...]"
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Performance** | Spatial Hash (Option 3) | 3x faster for your data (90% in $10-$1000 range) |
| **Fallback** | Binary search stashed | Available if buckets degrade |
| **Metadata Encoding** | `[key:value]` in notes | Future-proof, parseable, clean |
| **Conflict Resolution** | Beancount wins | PocketSmith never writes transfer metadata |
| **Suspected Transfers** | Metadata + comment | Programmatic + human-readable |
| **Category** | Find from main.beancount | Uses existing Transfer category ID |
| **Confidence Levels** | confirmed/suspected | Clear, simple naming |
| **Pattern Detection** | Automatic threshold=1 | Immediate feedback on systematic delays |

---

## Implementation Phases

### Phase 1: Foundation (2-3 hours)
- [ ] Extend `Transaction` model
- [ ] Update `beancount/write.py` for metadata
- [ ] Update `beancount/read.py` for metadata
- [ ] Update PocketSmith converters
- [ ] Create `metadata_encoding.py`

**Files**: 5 modified, 1 new

### Phase 2: Detection Engine (2-3 hours)
- [ ] Create `transfers/models.py`
- [ ] Create `transfers/detector.py` (Option 3 - Spatial Hash)
- [ ] Backup `detector_option1_backup.py`
- [ ] Implement confirmed detection
- [ ] Implement suspected detection
- [ ] Pattern notification

**Files**: 3 new

### Phase 3: Application Layer (1-2 hours)
- [ ] Create `transfers/applier.py`
- [ ] Create `transfers/category_helper.py`
- [ ] Create `cli/transfer_commands.py`
- [ ] Wire up to `main.py`
- [ ] Implement in-place ledger writing

**Files**: 3 new, 1 modified

### Phase 4: Interactive Mode (2-3 hours)
- [ ] Add `rich` dependency
- [ ] Interactive review UI
- [ ] Pattern-based suggestions
- [ ] Criteria adjustment
- [ ] Config file persistence (`.transfer-config.yaml`)
- [ ] Date range filtering

**Files**: 1 modified (transfer_commands.py)

### Phase 5: PocketSmith Sync (2-3 hours)
- [ ] Update `push.py` for transfer metadata
- [ ] Update `pull.py` for transfer metadata
- [ ] Beancount-wins merge strategy
- [ ] Note field encoding/decoding
- [ ] Transfer category lookup

**Files**: 2 modified

### Phase 6: Testing (3-4 hours)
- [ ] Test suite structure
- [ ] Idempotency tests (a-d)
- [ ] Detection logic tests
- [ ] Performance tests (20k txns)
- [ ] Metadata encoding tests
- [ ] Integration tests

**Files**: 6 new test files

---

## Total Effort Estimate

| Phase | Hours | Priority |
|-------|-------|----------|
| Phase 1 | 2-3 | P0 - Critical |
| Phase 2 | 2-3 | P0 - Critical |
| Phase 3 | 1-2 | P0 - Critical |
| Phase 4 | 2-3 | P1 - High |
| Phase 5 | 2-3 | P0 - Critical |
| Phase 6 | 3-4 | P0 - Critical |
| **Total** | **12-18** | |

**Realistic timeline**: 2-3 working days for complete implementation with tests.

---

## Dependencies to Add

```toml
# In pyproject.toml

[project]
dependencies = [
    # ... existing ...
    "rich>=13.0.0",  # For interactive CLI
]
```

---

## Configuration Files

### `.transfer-config.yaml` (created during interactive session)
```yaml
detection:
  max_date_difference_days: 3  # Adjusted from default 2
  fx_amount_tolerance_percent: 5.0
  max_suspected_date_days: 4

name_variations:
  - "Lok Sun Nelson Tam"
  - "Sophia S Tam"
  - "LSN Tam"
  - "N Tam"
  - "L Tam"
  - "S Tam"
  - "SS Tam"

fx_enabled_accounts:
  - "Wise"
  - "Revolut"  # Added by user
```

---

## CLI Commands Summary

```bash
# Detect all transfers in ledger
uv run python main.py detect-transfers

# Detect and apply confirmed only
uv run python main.py detect-transfers --apply --confidence confirmed

# Interactive review of suspected transfers
uv run python main.py detect-transfers --apply --interactive --confidence suspected

# Preview changes
uv run python main.py detect-transfers --apply --dry-run -v

# Specific date range
uv run python main.py detect-transfers --from 2024-01-01 --to 2024-12-31

# After marking transfers, sync to PocketSmith
uv run python main.py push
```

---

## Example Usage Workflow

```bash
# 1. Initial detection (dry run to see what would be found)
uv run python main.py detect-transfers --apply --dry-run -v

# Output:
# ✓ Confirmed transfers: 45
#   1001 ↔ 1002 ($150.00)
#   1003 ↔ 1004 ($500.00)
#   ...
# ? Suspected transfers: 12
#   2001 ↔ 2002 ($97.50) - amount-mismatch-fx
#   2003 ↔ 2004 ($200.00) - date-delay-3days
#   ...
# ⚠️  Pattern detected: 8 transfer(s) with 3-day delay

# 2. Apply confirmed transfers
uv run python main.py detect-transfers --apply --confidence confirmed

# Marked 90 transactions as confirmed transfers

# 3. Interactively review suspected
uv run python main.py detect-transfers --apply --interactive --confidence suspected

# [Interactive prompts for each pair]
# Adjust max_date_difference_days from 2 to 3? Yes
# ✓ Criteria adjusted!

# 4. Push to PocketSmith
uv run python main.py push

# 5. Verify idempotency
uv run python main.py pull
# (Ledger unchanged)
```

---

## Beancount File Format Examples

### Confirmed Transfer
```beancount
2024-01-15 * "Transfer" "To savings account"
  is_transfer: "true"
  paired: 1002
  id: 1001
  last_modified: "2024-01-15 10:30:00+11:00"
  Assets:Checking  -500.00 USD
  Expenses:Transfer  500.00 USD

2024-01-16 * "Transfer" "From checking"
  is_transfer: "true"
  paired: 1001
  id: 1002
  last_modified: "2024-01-16 08:15:00+11:00"
  Assets:Savings  500.00 USD
  Expenses:Transfer  -500.00 USD
```

### Suspected Transfer
```beancount
2024-01-20 * "International Transfer" "To Wise"
  ; Suspected transfer: amount-mismatch-fx, date-delay-3days
  paired: 2002
  suspect_reason: "amount-mismatch-fx, date-delay-3days"
  id: 2001
  Assets:Checking  -100.00 USD
  Expenses:Uncategorized  100.00 USD

2024-01-23 * "Transfer received" "From checking"
  ; Suspected transfer: amount-mismatch-fx, date-delay-3days
  paired: 2001
  suspect_reason: "amount-mismatch-fx, date-delay-3days"
  id: 2002
  Assets:Wise  97.50 USD
  Income:Uncategorized  -97.50 USD
```

---

## PocketSmith API Updates

### Confirmed Transfer (after push)
```json
{
  "id": 1001,
  "is_transfer": true,
  "note": "To savings account [paired:1002]",
  "category_id": 789,  // Transfer category
  "amount": -500.00
}
```

### Suspected Transfer (after push)
```json
{
  "id": 2001,
  "is_transfer": false,  // Not marked as transfer
  "note": "To Wise [paired:2002] [suspect_reason:amount-mismatch-fx, date-delay-3days]",
  "category_id": 123,  // Original category unchanged
  "amount": -100.00
}
```

---

## Performance Characteristics

### Spatial Hash Performance (Your Data: 19,864 txns)

```
Build Index:    ~5ms   (O(n))
Query/txn:      ~0.2ms (O(1) average)
Total:          ~10ms  (for full detection)

Memory: ~2MB (2 hash maps + transaction refs)
```

### Scalability

| Transactions | Build | Query | Total | Memory |
|--------------|-------|-------|-------|--------|
| 20k | 5ms | 4ms | 10ms | 2MB |
| 100k | 25ms | 20ms | 50ms | 10MB |
| 500k | 125ms | 100ms | 250ms | 50MB |
| 1M | 250ms | 200ms | 450ms | 100MB |

**Fallback trigger**: If any bucket exceeds 1,000 items, switch to Option 1 (binary search).

---

## Edge Cases Handled

1. **Cross-boundary dates**: Month/year boundaries work correctly
2. **Same account**: Prevents matching within same account
3. **Duplicate amounts**: Common amounts ($50, $100) handled via date filtering
4. **Multiple candidates**: Greedy matching (first valid pair wins)
5. **Already paired**: Won't re-pair transactions
6. **Missing metadata**: Gracefully handles missing accounts/dates
7. **Encoding conflicts**: Beancount always wins during pull
8. **Note field limits**: PocketSmith note field is ~1000 chars (plenty for metadata)

---

## Future Enhancements (Not in Scope)

- Multi-leg transfers (A → B → C)
- Currency conversion tracking
- Fee extraction
- Transfer categorization rules
- Bulk unpair command
- Transfer analytics dashboard
- Auto-reconciliation

---

## Detection Criteria

### High-Confidence (Confirmed) Transfers

Must meet ALL criteria:
1. **Different accounts**: Transactions from separate accounts
2. **Opposite directions**: One negative, one positive amount
3. **Same amount**: Exact match (within configured tolerance)
4. **Date proximity**: Within 2 days of each other (configurable)

### Low-Confidence (Suspected) Transfers

Must meet criterion 1, plus ONE OR MORE of:
1. **Same direction**: Both positive or both negative (violates confirmed rule)
2. **Amount mismatch (FX)**: Within 5% tolerance AND involves FX-enabled account (e.g., Wise)
3. **Date delay**: 3-4 days apart (outside confirmed window)
4. **Description-based**: Contains "transfer" AND name variation (regex match)

**All matching reasons are listed** in the suspect_reason field.

---

## Metadata Field Specifications

### Beancount Metadata Keys
- `is_transfer`: String "true" (for confirmed transfers only)
- `paired`: Integer transaction ID
- `suspect_reason`: String with comma-separated reasons

### PocketSmith API Fields
- `is_transfer`: Boolean (API field)
- `note`: String with `[key:value]` encoded metadata

### Encoding Format
Pattern: `[key:value]`

Examples:
- `[paired:12345]`
- `[suspect_reason:date-delay-3days]`
- Multiple: `"My note [paired:123] [suspect_reason:amount-mismatch-fx]"`

All metadata uses this standardized format for future compatibility.
