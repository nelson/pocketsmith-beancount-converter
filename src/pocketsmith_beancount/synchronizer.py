"""Main synchronization orchestrator for PocketSmith and beancount data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .sync_interfaces import SyncOrchestrator, SyncLogger
from .sync_models import SyncResult, SyncSummary
from .sync_enums import SyncStatus, SyncDirection
from .sync_exceptions import SynchronizationError, DataIntegrityError
from .transaction_comparator import PocketSmithTransactionComparator
from .resolution_engine import ResolutionEngine
from .api_writer import PocketSmithAPIWriter, MockAPIWriter
from .changelog import TransactionChangelog

logger = logging.getLogger(__name__)


class PocketSmithSynchronizer(SyncOrchestrator):
    """Main synchronization orchestrator for PocketSmith data."""

    def __init__(
        self,
        api_writer: Optional[PocketSmithAPIWriter] = None,
        changelog: Optional[TransactionChangelog] = None,
        sync_logger: Optional[SyncLogger] = None,
    ):
        self.comparator = PocketSmithTransactionComparator()
        self.resolution_engine = ResolutionEngine()
        self.api_writer = api_writer or MockAPIWriter()
        self.changelog = changelog
        self.sync_logger = sync_logger or ConsoleSyncLogger()

    def synchronize(
        self,
        local_transactions: List[Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> List[SyncResult]:
        """
        Synchronize local and remote transactions.

        Args:
            local_transactions: List of local transaction data
            remote_transactions: List of remote transaction data
            dry_run: If True, don't make actual changes

        Returns:
            List of synchronization results
        """
        summary = SyncSummary(dry_run=dry_run, start_time=datetime.now())
        results = []

        try:
            # Prepare for synchronization
            if not self.prepare_sync(local_transactions, remote_transactions):
                raise SynchronizationError("Synchronization preparation failed")

            # Log sync start
            self.sync_logger.log_sync_start(
                len(local_transactions) + len(remote_transactions), dry_run
            )

            # Match transactions by ID
            matched_pairs, local_only, remote_only = (
                self.comparator.match_transactions_by_id(
                    local_transactions, remote_transactions
                )
            )

            logger.info(
                f"Transaction matching: {len(matched_pairs)} matched, "
                f"{len(local_only)} local-only, {len(remote_only)} remote-only"
            )

            # Process matched transactions
            for local_tx, remote_tx in matched_pairs:
                result = self._sync_transaction_pair(local_tx, remote_tx, dry_run)
                results.append(result)
                summary.add_result(result)
                self.sync_logger.log_transaction_sync(result)

            # Process local-only transactions (exist in beancount but not PocketSmith)
            for local_tx in local_only:
                result = self._handle_local_only_transaction(local_tx, dry_run)
                results.append(result)
                summary.add_result(result)
                self.sync_logger.log_transaction_sync(result)

            # Process remote-only transactions (exist in PocketSmith but not beancount)
            for remote_tx in remote_only:
                result = self._handle_remote_only_transaction(remote_tx, dry_run)
                results.append(result)
                summary.add_result(result)
                self.sync_logger.log_transaction_sync(result)

            # Finalize synchronization
            summary.end_time = datetime.now()
            self._finalize_sync(summary, results, dry_run)

            logger.info(
                f"Synchronization completed: {summary.successful_syncs}/{summary.total_transactions} successful, "
                f"{summary.conflicts_detected} conflicts, {summary.errors_encountered} errors"
            )

        except Exception as e:
            summary.end_time = datetime.now()
            error_msg = f"Synchronization failed: {e}"
            logger.error(error_msg)
            self.sync_logger.log_error(error_msg)
            raise SynchronizationError(error_msg)

        return results

    def prepare_sync(
        self,
        local_transactions: List[Dict[str, Any]],
        remote_transactions: List[Dict[str, Any]],
    ) -> bool:
        """
        Prepare for synchronization (validation, setup, etc.).

        Args:
            local_transactions: List of local transaction data
            remote_transactions: List of remote transaction data

        Returns:
            True if preparation was successful
        """
        try:
            # Validate transaction data
            self._validate_transaction_data(local_transactions, "local")
            self._validate_transaction_data(remote_transactions, "remote")

            # Check for field coverage
            all_fields: set[str] = set()
            for tx in local_transactions + remote_transactions:
                all_fields.update(tx.keys())

            unmapped_fields = self.resolution_engine.validate_resolution_completeness(
                list(all_fields)
            )
            if unmapped_fields:
                logger.warning(f"Unmapped fields detected: {unmapped_fields}")

            return True

        except Exception as e:
            logger.error(f"Synchronization preparation failed: {e}")
            return False

    def _sync_transaction_pair(
        self, local_tx: Dict[str, Any], remote_tx: Dict[str, Any], dry_run: bool
    ) -> SyncResult:
        """Synchronize a matched pair of local and remote transactions."""
        transaction_id = str(remote_tx.get("id", local_tx.get("id", "unknown")))

        try:
            # Resolve conflicts between local and remote data
            result = self.resolution_engine.resolve_transaction(
                local_tx, remote_tx, transaction_id
            )

            # Check if write-back is needed
            write_back_data = self.resolution_engine.get_write_back_fields(result)

            if write_back_data:
                try:
                    # Perform write-back to remote API
                    success = self.api_writer.update_transaction(
                        transaction_id, write_back_data, dry_run
                    )

                    if success:
                        result.sync_direction = SyncDirection.LOCAL_TO_REMOTE
                        logger.info(
                            f"Successfully wrote back changes for transaction {transaction_id}"
                        )
                    else:
                        result.add_error("Failed to write back changes to remote")
                        result.status = SyncStatus.ERROR

                except Exception as e:
                    result.add_error(f"Write-back failed: {e}")
                    result.status = SyncStatus.ERROR

            # Log to changelog if available
            if self.changelog and result.has_changes:
                field_changes = {
                    change.field_name: (change.old_value, change.new_value)
                    for change in result.changes
                }
                self.changelog.log_transaction_modify(transaction_id, field_changes)

            return result

        except Exception as e:
            error_result = SyncResult(
                transaction_id=transaction_id, status=SyncStatus.ERROR
            )
            error_result.add_error(f"Failed to sync transaction: {e}")
            return error_result

    def _handle_local_only_transaction(
        self, local_tx: Dict[str, Any], dry_run: bool
    ) -> SyncResult:
        """Handle transaction that exists only in local beancount data."""
        transaction_id = str(local_tx.get("id", "unknown"))

        # For now, we just log this as informational
        # In the future, we might want to create the transaction remotely
        result = SyncResult(transaction_id=transaction_id, status=SyncStatus.SKIPPED)
        result.add_warning(
            "Transaction exists only in local data - no remote sync performed"
        )

        logger.info(f"Local-only transaction {transaction_id} - skipping sync")
        return result

    def _handle_remote_only_transaction(
        self, remote_tx: Dict[str, Any], dry_run: bool
    ) -> SyncResult:
        """Handle transaction that exists only in remote PocketSmith data."""
        transaction_id = str(remote_tx.get("id", "unknown"))

        # For now, we just log this as informational
        # In the future, we might want to add the transaction to local beancount
        result = SyncResult(transaction_id=transaction_id, status=SyncStatus.SKIPPED)
        result.add_warning(
            "Transaction exists only in remote data - no local sync performed"
        )

        logger.info(f"Remote-only transaction {transaction_id} - skipping sync")
        return result

    def _validate_transaction_data(
        self, transactions: List[Dict[str, Any]], source: str
    ) -> None:
        """Validate transaction data integrity."""
        for i, tx in enumerate(transactions):
            if not isinstance(tx, dict):
                raise DataIntegrityError(
                    f"Invalid transaction data at index {i} in {source}: not a dictionary"
                )

            # Check for required ID field
            tx_id = tx.get("id")
            if tx_id is None:
                raise DataIntegrityError(
                    f"Missing transaction ID at index {i} in {source}"
                )

            # Validate critical fields exist and have reasonable values
            if source == "remote":
                if "amount" not in tx:
                    raise DataIntegrityError(
                        f"Missing amount field in {source} transaction {tx_id}"
                    )

                if "date" not in tx:
                    raise DataIntegrityError(
                        f"Missing date field in {source} transaction {tx_id}"
                    )

    def _finalize_sync(
        self, summary: SyncSummary, results: List[SyncResult], dry_run: bool
    ) -> None:
        """Finalize synchronization with cleanup and reporting."""
        # Log summary
        summary_data = {
            "total_transactions": summary.total_transactions,
            "successful_syncs": summary.successful_syncs,
            "conflicts_detected": summary.conflicts_detected,
            "errors_encountered": summary.errors_encountered,
            "warnings_generated": summary.warnings_generated,
            "changes_made": summary.changes_made,
            "duration": summary.duration,
            "success_rate": summary.success_rate,
            "dry_run": dry_run,
        }

        self.sync_logger.log_sync_complete(summary_data)

        # Log any conflicts that need attention
        for result in results:
            for conflict in result.conflicts:
                self.sync_logger.log_conflict(conflict)


class ConsoleSyncLogger(SyncLogger):
    """Console-based sync logger implementation."""

    def log_sync_start(self, transaction_count: int, dry_run: bool = False) -> None:
        """Log the start of synchronization."""
        mode = "DRY RUN" if dry_run else "LIVE"
        logger.info(
            f"Starting synchronization ({mode}) for {transaction_count} transactions"
        )

    def log_sync_complete(self, summary: Dict[str, Any]) -> None:
        """Log the completion of synchronization."""
        mode = "DRY RUN" if summary.get("dry_run") else "LIVE"
        duration = summary.get("duration", 0)
        success_rate = summary.get("success_rate", 0)

        logger.info(
            f"Synchronization complete ({mode}): "
            f"{summary['successful_syncs']}/{summary['total_transactions']} successful "
            f"({success_rate:.1f}%), {summary['changes_made']} changes made, "
            f"duration: {duration:.2f}s"
        )

        if summary.get("conflicts_detected", 0) > 0:
            logger.warning(
                f"Detected {summary['conflicts_detected']} conflicts requiring attention"
            )

        if summary.get("errors_encountered", 0) > 0:
            logger.error(
                f"Encountered {summary['errors_encountered']} errors during sync"
            )

    def log_transaction_sync(self, result: SyncResult) -> None:
        """Log the result of syncing a single transaction."""
        if result.status == SyncStatus.SUCCESS and result.has_changes:
            change_summary = ", ".join(
                [
                    f"{change.field_name}: {change.old_value} -> {change.new_value}"
                    for change in result.changes[:3]  # Show first 3 changes
                ]
            )
            if len(result.changes) > 3:
                change_summary += f" (and {len(result.changes) - 3} more)"

            logger.info(f"Synced transaction {result.transaction_id}: {change_summary}")

        elif result.status == SyncStatus.ERROR:
            logger.error(
                f"Failed to sync transaction {result.transaction_id}: {'; '.join(result.errors)}"
            )

        elif result.status == SyncStatus.SKIPPED:
            logger.debug(
                f"Skipped transaction {result.transaction_id}: {'; '.join(result.warnings)}"
            )

    def log_conflict(self, conflict: Any) -> None:
        """Log a synchronization conflict."""
        logger.warning(
            f"CONFLICT in transaction {conflict.transaction_id}, field '{conflict.field_name}': "
            f"local='{conflict.local_value}' vs remote='{conflict.remote_value}' "
            f"(strategy: {conflict.strategy.name})"
        )

    def log_error(self, error: str, transaction_id: Optional[str] = None) -> None:
        """Log an error during synchronization."""
        if transaction_id:
            logger.error(f"Transaction {transaction_id}: {error}")
        else:
            logger.error(error)

    def log_warning(self, warning: str, transaction_id: Optional[str] = None) -> None:
        """Log a warning during synchronization."""
        if transaction_id:
            logger.warning(f"Transaction {transaction_id}: {warning}")
        else:
            logger.warning(warning)
