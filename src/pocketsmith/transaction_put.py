"""Transaction update operations for PocketSmith API."""

import logging
import time
from typing import Any, Dict, List, Optional
import requests

from .common import (
    PocketSmithClient,
    PocketSmithAPIError,
    RateLimiter,
    validate_update_data,
    convert_to_api_format,
)

logger = logging.getLogger(__name__)


def update_transaction(
    transaction_id: str,
    updates: Dict[str, Any],
    dry_run: bool = False,
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> bool:
    """Update a transaction via API."""
    if client is None:
        client = PocketSmithClient(api_key)

    rate_limiter = RateLimiter()

    try:
        # Validate update data
        if not validate_update_data(updates):
            return False

        # Convert updates to API format
        api_updates = convert_to_api_format(updates)

        if dry_run:
            logger.info(
                f"DRY RUN: Would update transaction {transaction_id} with: {api_updates}"
            )
            return True

        # Apply rate limiting
        rate_limiter.wait_if_needed()

        # Make API request
        url = f"{client.base_url}/transactions/{transaction_id}"

        logger.info(f"Updating transaction {transaction_id} with: {api_updates}")

        response = requests.put(
            url,
            headers={**client.headers, "Content-Type": "application/json"},
            json=api_updates,
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)

            # Retry the request
            response = requests.put(
                url,
                headers={**client.headers, "Content-Type": "application/json"},
                json=api_updates,
            )

        if response.status_code == 200:
            logger.info(f"Successfully updated transaction {transaction_id}")
            return True
        else:
            error_msg = f"Failed to update transaction {transaction_id}: {response.status_code} {response.text}"
            logger.error(error_msg)
            raise PocketSmithAPIError(
                error_msg,
                transaction_id=transaction_id,
                status_code=response.status_code,
                response_body=response.text,
            )

    except requests.RequestException as e:
        error_msg = f"Network error updating transaction {transaction_id}: {e}"
        logger.error(error_msg)
        raise PocketSmithAPIError(error_msg, transaction_id=transaction_id)

    except Exception as e:
        error_msg = f"Unexpected error updating transaction {transaction_id}: {e}"
        logger.error(error_msg)
        raise PocketSmithAPIError(error_msg, transaction_id=transaction_id)


def update_transaction_note(
    transaction_id: str,
    note: str,
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a transaction's note field."""
    if client is None:
        client = PocketSmithClient(api_key)

    data = {"note": note}
    return client._make_put_request(f"transactions/{transaction_id}", data)


def update_transaction_labels(
    transaction_id: str,
    labels: List[str],
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a transaction's labels field."""
    if client is None:
        client = PocketSmithClient(api_key)

    data = {"labels": labels}
    return client._make_put_request(f"transactions/{transaction_id}", data)


def batch_update_transactions(
    updates: List[Dict[str, Any]],
    dry_run: bool = False,
    client: Optional[PocketSmithClient] = None,
    api_key: Optional[str] = None,
) -> List[bool]:
    """Update multiple transactions in batch."""
    if client is None:
        client = PocketSmithClient(api_key)

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
            success = update_transaction(transaction_id, field_updates, dry_run, client)
            results.append(success)

            # Add delay between requests to be respectful to API
            if not dry_run:
                time.sleep(0.1)  # 100ms delay

        except PocketSmithAPIError as e:
            logger.error(f"Failed to update transaction {transaction_id} in batch: {e}")
            results.append(False)

    successful_updates = sum(results)
    logger.info(
        f"Batch update completed: {successful_updates}/{len(updates)} successful"
    )

    return results
