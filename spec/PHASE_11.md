# Phase 11 — Push, CLI Addendum, Rules Addendum

This phase delivers the `push` feature, CLI improvements, and rule engine addenda.

## Goals

- Implement `peabody push` to write local changes back to PocketSmith.
- Prefer local category changes during push (Strategy 2 for `category`).
- Add changelog entries for `PUSH` and per-field `UPDATE`s.
- Extend CLI: add `help` command, hide convenience date options, and add `--id` for `pull`, `push`, `diff`.
- Rule addendum: preconditions with `metadata` and use `APPLY` in changelog for rule applications.

## Implementation Plan

1. CLI
   - Add `src/cli/push.py` and wire `main.push` to it.
   - Add `--id` support to `diff` (and ensure for `push`).
   - Keep convenience date options hidden (already done).
   - Keep `help` command listing subcommands (already exists; update text).

2. Changelog
   - Add `write_push_entry([FROM] [TO])`.
   - Reuse `write_update_entry` for per-field updates during push.

3. Push Command
   - Determine date range from latest `CLONE`/`PULL` if none specified.
   - If `--id` provided, fetch only that transaction.
   - Perform an internal diff (placeholder using current local read stubs).
   - For differing fields, resolve with category = Local priority; generate updates.
   - Write updates to PocketSmith via client; honor `--dry-run` and `--quiet`.
   - Log `PUSH` and `UPDATE` entries (skip when `--dry-run`).

4. Rules Addendum
   - Preconditions with `metadata` already supported in loader/matcher.
   - Ensure `rule apply` logs `APPLY ...` lines to changelog when not dry-run.

5. Minimal Refactor
   - Reuse `DateOptions` and common helpers to minimize duplication.

## Notes / Limitations

- Local beancount reading remains a stub; push will no-op if no differences are detected. This preserves behavior and interfaces; actual beancount parsing can be added later.
- Category updates are supported by sending `category_id` in API updates.

## Testing Focus

- CLI accepts new options and routes correctly.
- Changelog writes `PUSH` and `UPDATE` entries (skipped in dry-run).
- `rule apply` writes `APPLY` entries to changelog.

