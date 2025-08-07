# PocketSmith to Beancount Converter - Testing Documentation

## Testing Requirements

### 🧪 Testing Requirements
- [x] **Write unit tests for bug fixes** - Comprehensive test coverage for all bug fixes ✅ COMPLETED
- [x] **Write unit tests for new features** - Test coverage for all new functionality ✅ COMPLETED

### ✅ Unit Tests Analysis (Current: 79 tests - Target Exceeded!) - **COMPLETED**

#### **PocketSmithClient Tests** (10 → 18 total tests) ✅ COMPLETED
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

#### **BeancountConverter Tests** (23 → 35 total tests) ✅ COMPLETED
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

#### **BeancountFileWriter Tests** (10 total tests) ✅ COMPLETED
**Implemented:**
- [x] **`test_init_with_env_var()`** - Test initialization with BEANCOUNT_OUTPUT_DIR environment variable ✅ COMPLETED
- [x] **`test_write_file_creates_directory()`** - Test that output directory is created if it doesn't exist ✅ COMPLETED
- [x] **`test_write_file_with_extension_already_present()`** - Test filename handling when .beancount extension already exists ✅ COMPLETED
- [x] **`test_append_to_nonexistent_file()`** - Test appending to a file that doesn't exist yet ✅ COMPLETED

#### **Main Module Tests** (6 → 9 total tests) ✅ COMPLETED - **HIGH PRIORITY**
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

#### **Integration Tests** (4 → 7 total tests) ✅ COMPLETED - **MEDIUM PRIORITY**
**Existing Tests (4):**
- [x] **`test_end_to_end_conversion()`** - Test full pipeline with mock data ✅ COMPLETED
- [x] **`test_multiple_currencies()`** - Test handling of multiple currencies in one conversion ✅ COMPLETED
- [x] **`test_large_transaction_set()`** - Test performance with large datasets ✅ COMPLETED
- [x] **`test_special_characters_in_data()`** - Test handling of special characters in account names, payees, etc. ✅ COMPLETED

**New Phase 5 Tests (3 additional):**
- [x] **`test_end_to_end_with_labels_and_flags()`** - Test full pipeline with labels and needs_review ✅ COMPLETED
- [x] **`test_end_to_end_with_balance_directives()`** - Test full pipeline with balance directives ✅ COMPLETED
- [x] **`test_pagination_integration()`** - Test pagination in full pipeline ✅ COMPLETED

### ✅ **Test Coverage Summary** - **COMPLETED**
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

## New Testing Requirements

### Quality Improvement A: Real API Endpoint Unit Tests
For each API endpoint that we are using, write a unit test that actually calls the endpoint instead of relying on mock responses. For every data field that we are consuming from those endpoints, those unit tests should ensure we are getting valid data. Try to validate fields that are not populated by "null values" such as the empty string, zero, or False.

**Required Tests:**
- [ ] **`test_real_api_get_accounts()`** - Test actual PocketSmith accounts endpoint
  - Validate account ID is not empty/zero
  - Validate account name is not empty string
  - Validate account type is valid enum value
  - Validate currency_code is valid 3-letter code
  - Validate institution data when present
- [ ] **`test_real_api_get_categories()`** - Test actual PocketSmith categories endpoint
  - Validate category ID is not empty/zero
  - Validate category title is not empty string
  - Validate parent_id relationships are consistent
  - Validate colour field format when present
- [ ] **`test_real_api_get_transaction_accounts()`** - Test actual transaction accounts endpoint
  - Validate transaction account ID is not empty/zero
  - Validate account_id references valid account
  - Validate starting_balance is numeric when present
  - Validate starting_balance_date format when present
- [ ] **`test_real_api_get_transactions()`** - Test actual transactions endpoint
  - Validate transaction ID is not empty/zero
  - Validate payee is not empty when present
  - Validate amount is not zero
  - Validate date format is valid
  - Validate currency_code matches account currency
  - Validate labels array structure
  - Validate needs_review is boolean
  - Validate updated_at timestamp format
  - Validate closing_balance is numeric when present
- [ ] **`test_real_api_get_account_balances()`** - Test actual account balances endpoint
  - Validate balance amount is numeric
  - Validate date format is valid
  - Validate account_id references valid account

### Quality Improvement B: Hypothesis Property-Based Testing
Add hypothesis property-based testing (https://hypothesis.readthedocs.io/en/latest/) into our unit tests. Just apply it to a few simple tests first.

**Required Tests:**
- [ ] **`test_property_account_name_sanitization()`** - Property test for account name cleaning
  - Generate random strings with various special characters
  - Ensure sanitized names are valid beancount account names
  - Ensure no leading/trailing underscores or hyphens
- [ ] **`test_property_transaction_amount_conversion()`** - Property test for amount handling
  - Generate random decimal amounts (positive/negative)
  - Ensure proper decimal precision is maintained
  - Ensure currency formatting is consistent
- [ ] **`test_property_date_parsing()`** - Property test for date string handling
  - Generate various date formats from PocketSmith
  - Ensure all valid dates are parsed correctly
  - Ensure invalid dates raise appropriate errors
- [ ] **`test_property_label_tag_conversion()`** - Property test for label sanitization
  - Generate random label strings with special characters
  - Ensure all labels convert to valid beancount tags
  - Ensure tag uniqueness is maintained

**Dependencies to Add:**
- Add `hypothesis` to development dependencies in pyproject.toml
- Import hypothesis strategies in relevant test files
- Configure hypothesis settings for test performance

## Test Execution Commands
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src

# Run specific test categories
uv run pytest tests/test_pocketsmith_client.py  # API client tests
uv run pytest tests/test_beancount_converter.py # Converter tests
uv run pytest tests/test_integration.py         # Integration tests

# Run property-based tests specifically
uv run pytest -k "property" -v

# Run real API tests (requires valid API key)
uv run pytest -k "real_api" -v
```