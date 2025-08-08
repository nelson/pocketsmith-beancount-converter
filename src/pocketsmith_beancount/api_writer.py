"""API write-back functionality for updating PocketSmith transactions."""

import logging
import time
from typing import Any, Dict, List
import requests

from .sync_interfaces import APIWriter
from .sync_exceptions import APIWriteBackError
from .field_mapping import FieldMapping

logger = logging.getLogger(__name__)


class PocketSmithAPIWriter(APIWriter):
    """Implementation of API write-back for PocketSmith."""

    def __init__(self, api_key: str, base_url: str = "https://api.pocketsmith.com/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-Developer-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.field_mapping = FieldMapping()
        self.rate_limiter = RateLimiter()

    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any], dry_run: bool = False
    ) -> bool:
        """
        Update a transaction via API.

        Args:
            transaction_id: ID of transaction to update
            updates: Dictionary of field updates
            dry_run: If True, don't actually make the API call

        Returns:
            True if update was successful
        """
        try:
            # Validate update data
            if not self.validate_update_data(transaction_id, updates):
                return False

            # Convert updates to API format
            api_updates = self._convert_to_api_format(updates)

            if dry_run:
                logger.info(
                    f"DRY RUN: Would update transaction {transaction_id} with: {api_updates}"
                )
                return True

            # Apply rate limiting
            self.rate_limiter.wait_if_needed()

            # Make API request
            url = f"{self.base_url}/transactions/{transaction_id}"

            logger.info(f"Updating transaction {transaction_id} with: {api_updates}")

            response = requests.put(url, headers=self.headers, json=api_updates)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)

                # Retry the request
                response = requests.put(url, headers=self.headers, json=api_updates)

            if response.status_code == 200:
                logger.info(f"Successfully updated transaction {transaction_id}")
                return True
            else:
                error_msg = f"Failed to update transaction {transaction_id}: {response.status_code} {response.text}"
                logger.error(error_msg)
                raise APIWriteBackError(
                    error_msg,
                    transaction_id=transaction_id,
                    status_code=response.status_code,
                    response_body=response.text,
                )

        except requests.RequestException as e:
            error_msg = f"Network error updating transaction {transaction_id}: {e}"
            logger.error(error_msg)
            raise APIWriteBackError(error_msg, transaction_id=transaction_id)

        except Exception as e:
            error_msg = f"Unexpected error updating transaction {transaction_id}: {e}"
            logger.error(error_msg)
            raise APIWriteBackError(error_msg, transaction_id=transaction_id)

    def batch_update_transactions(
        self, updates: List[Dict[str, Any]], dry_run: bool = False
    ) -> List[bool]:
        """
        Update multiple transactions in batch.

        Args:
            updates: List of update dictionaries with transaction_id and fields
            dry_run: If True, don't actually make API calls

        Returns:
            List of success/failure results
        """
        results = []

        for update in updates:
            transaction_id = update.get("transaction_id")
            if not transaction_id:
                logger.error("Missing transaction_id in batch update")
                results.append(False)
                continue

            # Extract field updates (everything except transaction_id)
            field_updates = {k: v for k, v in update.items() if k != "transaction_id"}

            try:
                success = self.update_transaction(
                    transaction_id, field_updates, dry_run
                )
                results.append(success)

                # Add delay between requests to be respectful to API
                if not dry_run:
                    time.sleep(0.1)  # 100ms delay

            except APIWriteBackError as e:
                logger.error(
                    f"Failed to update transaction {transaction_id} in batch: {e}"
                )
                results.append(False)

        successful_updates = sum(results)
        logger.info(
            f"Batch update completed: {successful_updates}/{len(updates)} successful"
        )

        return results

    def validate_update_data(
        self, transaction_id: str, updates: Dict[str, Any]
    ) -> bool:
        """
        Validate update data before sending to API.

        Args:
            transaction_id: ID of transaction to update
            updates: Dictionary of field updates

        Returns:
            True if data is valid
        """
        if not transaction_id:
            logger.error("Transaction ID is required for updates")
            return False

        if not updates:
            logger.warning(f"No updates provided for transaction {transaction_id}")
            return False

        # Check that all fields are writable
        for field_name in updates.keys():
            if not self.field_mapping.is_writable(field_name):
                logger.error(f"Field '{field_name}' is not writable via API")
                return False

        # Validate specific field formats
        for field_name, value in updates.items():
            if not self._validate_field_value(field_name, value):
                logger.error(f"Invalid value for field '{field_name}': {value}")
                return False

        return True

    def _convert_to_api_format(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal field names/values to API format."""
        api_updates = {}

        for field_name, value in updates.items():
            # Map internal field names to API field names
            api_field_name = self._map_field_name_to_api(field_name)

            # Convert value to API format
            api_value = self._convert_value_to_api_format(field_name, value)

            api_updates[api_field_name] = api_value

        return api_updates

    def _map_field_name_to_api(self, field_name: str) -> str:
        """Map internal field names to API field names."""
        field_mapping = {
            "note": "note",
            "memo": "memo",
            "labels": "labels",
            "tags": "labels",  # Tags map to labels in API
        }

        return field_mapping.get(field_name, field_name)

    def _convert_value_to_api_format(self, field_name: str, value: Any) -> Any:
        """Convert field value to API-expected format."""
        if field_name in ["labels", "tags"]:
            # Ensure labels are sent as a list of strings
            if isinstance(value, list):
                return [str(item) for item in value]
            elif value:
                return [str(value)]
            else:
                return []

        if field_name in ["note", "memo"]:
            # Ensure notes are strings
            return str(value) if value is not None else ""

        return value

    def _validate_field_value(self, field_name: str, value: Any) -> bool:
        """Validate a field value."""
        if field_name in ["labels", "tags"]:
            # Labels should be a list or convertible to list
            if value is None:
                return True
            if isinstance(value, list):
                return all(isinstance(item, (str, int, float)) for item in value)
            return isinstance(value, (str, int, float))

        if field_name in ["note", "memo"]:
            # Notes should be strings or None
            return value is None or isinstance(value, str)

        return True


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float = 2.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()


class MockAPIWriter(APIWriter):
    """Mock API writer for testing purposes."""

    def __init__(self) -> None:
        self.updates_made: list[Dict[str, Any]] = []
        self.should_fail = False
        self.fail_transaction_ids: set[str] = set()

    def update_transaction(
        self, transaction_id: str, updates: Dict[str, Any], dry_run: bool = False
    ) -> bool:
        """Mock update transaction."""
        if self.should_fail or transaction_id in self.fail_transaction_ids:
            raise APIWriteBackError(f"Mock failure for transaction {transaction_id}")

        self.updates_made.append(
            {"transaction_id": transaction_id, "updates": updates, "dry_run": dry_run}
        )

        return True

    def batch_update_transactions(
        self, updates: List[Dict[str, Any]], dry_run: bool = False
    ) -> List[bool]:
        """Mock batch update transactions."""
        results = []

        for update in updates:
            transaction_id = update.get("transaction_id")
            if not transaction_id:
                results.append(False)
                continue
            field_updates = {k: v for k, v in update.items() if k != "transaction_id"}

            try:
                success = self.update_transaction(
                    transaction_id, field_updates, dry_run
                )
                results.append(success)
            except APIWriteBackError:
                results.append(False)

        return results

    def validate_update_data(
        self, transaction_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Mock validation - always returns True unless configured otherwise."""
        return True

    def get_updates_made(self) -> list[Dict[str, Any]]:
        """Get list of updates that were made."""
        return self.updates_made

    def set_should_fail(self, should_fail: bool) -> None:
        """Configure whether to fail updates."""
        self.should_fail = should_fail

    def set_fail_for_transaction(self, transaction_id: str) -> None:
        """Configure mock to fail for specific transaction."""
        self.fail_transaction_ids.add(transaction_id)

    def clear_updates(self) -> None:
        """Clear the list of updates made."""
        self.updates_made.clear()
