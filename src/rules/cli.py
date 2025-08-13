"""CLI interface for transaction rule management."""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import colorama
from colorama import Fore, Style

from ..pocketsmith_beancount.changelog import TransactionChangelog
from .loader import RuleLoader
from .matcher import RuleMatcher
from .models import RuleApplicationBatch, RuleTransform, TransactionRule
from .transformer import RuleTransformer


class RuleCLI:
    """Command-line interface for rule operations."""

    def __init__(self) -> None:
        """Initialize the rule CLI."""
        colorama.init(autoreset=True)
        self.rule_loader = RuleLoader()
        self.rule_matcher = RuleMatcher()

    def handle_apply_command(
        self,
        args: argparse.Namespace,
        transactions: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
    ) -> None:
        """Handle the apply command to apply rules to transactions.

        Args:
            args: Parsed command line arguments
            transactions: List of transactions from PocketSmith
            categories: List of categories from PocketSmith
        """
        print(f"{Fore.CYAN}Applying transaction rules...{Style.RESET_ALL}")

        # Load rules
        rules_path = Path(args.rules_file) if args.rules_file else Path("rules.yaml")
        if not rules_path.exists():
            print(
                f"{Fore.RED}Error: Rules file not found: {rules_path}{Style.RESET_ALL}"
            )
            sys.exit(1)

        print(f"Loading rules from: {rules_path}")
        rule_result = self.rule_loader.load_rules(rules_path)

        if not rule_result.is_successful:
            print(
                f"{Fore.RED}Rule loading failed with {len(rule_result.errors)} errors:{Style.RESET_ALL}"
            )
            for error in rule_result.errors:
                print(f"  {Fore.RED}• {error}{Style.RESET_ALL}")
            sys.exit(1)

        print(
            f"{Fore.GREEN}Loaded {rule_result.rule_count} rules successfully{Style.RESET_ALL}"
        )

        # Filter transactions if specific IDs provided
        if args.transaction_ids:
            transaction_id_set = set(str(tid) for tid in args.transaction_ids)
            filtered_transactions = [
                t for t in transactions if str(t.get("id", "")) in transaction_id_set
            ]
            print(f"Filtered to {len(filtered_transactions)} specific transactions")
            transactions = filtered_transactions

        # Initialize changelog
        changelog = TransactionChangelog(args.output_dir or "output")

        # Apply rules
        batch_result = self._apply_rules_to_transactions(
            transactions, rule_result.rules, categories, changelog, args.dry_run
        )

        # Print results
        self._print_application_results(batch_result, args.dry_run)

        if args.dry_run:
            print(f"{Fore.YELLOW}DRY RUN: No actual changes were made{Style.RESET_ALL}")

    def handle_add_rule_command(self, args: argparse.Namespace) -> None:
        """Handle the add-rule command to create new rules.

        Args:
            args: Parsed command line arguments
        """
        print(f"{Fore.CYAN}Adding new transaction rule...{Style.RESET_ALL}")

        if args.interactive:
            self._add_rule_interactive()
        else:
            self._add_rule_from_args(args)

    def _apply_rules_to_transactions(
        self,
        transactions: List[Dict[str, Any]],
        rules: List[TransactionRule],
        categories: List[Dict[str, Any]],
        changelog: TransactionChangelog,
        dry_run: bool = False,
    ) -> RuleApplicationBatch:
        """Apply rules to a list of transactions.

        Args:
            transactions: List of transactions to process
            rules: List of rules to apply
            categories: List of categories for ID resolution
            changelog: Changelog instance for logging
            dry_run: If True, don't make actual changes

        Returns:
            RuleApplicationBatch with results
        """
        batch = RuleApplicationBatch()
        batch.rules_loaded = len(rules)
        batch.transactions_processed = len(transactions)

        # Prepare matcher with rules
        self.rule_matcher.prepare_rules(rules)

        # Initialize transformer
        transformer = RuleTransformer(categories, changelog)

        print(
            f"Processing {len(transactions)} transactions against {len(rules)} rules..."
        )

        for i, transaction in enumerate(transactions, 1):
            if i % 100 == 0 or i == len(transactions):
                print(f"  Progress: {i}/{len(transactions)} transactions")

            # Find matching rule
            match_result = self.rule_matcher.find_matching_rule(transaction, rules)

            if match_result:
                rule, regex_matches = match_result

                print(f"  Transaction {transaction.get('id')} matched rule {rule.id}")

                if not dry_run:
                    # Apply transformation
                    applications = transformer.apply_transform(
                        transaction, rule.transform, rule.id, regex_matches
                    )

                    # Log applications
                    transformer.log_applications(applications)

                    # Add to batch results
                    for app in applications:
                        batch.add_application(app)
                else:
                    # Dry run - just report what would be changed
                    print(
                        f"    Would apply: {self._describe_transform(rule.transform)}"
                    )

        return batch

    def _describe_transform(self, transform: RuleTransform) -> str:
        """Create a human-readable description of a transform."""
        parts = []

        if transform.category:
            parts.append(f"category → {transform.category}")

        if transform.get_effective_labels():
            labels = transform.get_effective_labels()
            if labels:
                parts.append(f"labels → {', '.join(labels)}")

        if transform.get_effective_memo():
            parts.append(f"memo → {transform.get_effective_memo()}")

        if transform.metadata:
            metadata_desc = ", ".join(f"{k}={v}" for k, v in transform.metadata.items())
            parts.append(f"metadata → {metadata_desc}")

        return "; ".join(parts) if parts else "no changes"

    def _print_application_results(
        self, batch: RuleApplicationBatch, dry_run: bool
    ) -> None:
        """Print rule application results summary.

        Args:
            batch: Rule application results
            dry_run: Whether this was a dry run
        """
        print(f"\n{Fore.CYAN}Rule Application Summary:{Style.RESET_ALL}")
        print(f"  Rules loaded: {batch.rules_loaded}")
        print(f"  Transactions processed: {batch.transactions_processed}")
        print(f"  Transactions matched: {batch.transactions_matched}")

        if not dry_run:
            print(
                f"  Successful applications: {Fore.GREEN}{batch.success_count}{Style.RESET_ALL}"
            )

            if batch.error_count > 0:
                print(
                    f"  Failed applications: {Fore.RED}{batch.error_count}{Style.RESET_ALL}"
                )

            if batch.warning_count > 0:
                print(
                    f"  Applications with warnings: {Fore.YELLOW}{batch.warning_count}{Style.RESET_ALL}"
                )

            # Show detailed errors
            if batch.failed_applications:
                print(f"\n{Fore.RED}Failed Applications:{Style.RESET_ALL}")
                for app in batch.failed_applications:
                    print(
                        f"  • Transaction {app.transaction_id}, Rule {app.rule_id}: {app.error_message}"
                    )

            # Show warnings
            if batch.applications_with_warnings:
                print(f"\n{Fore.YELLOW}Warnings:{Style.RESET_ALL}")
                for app in batch.applications_with_warnings:
                    print(
                        f"  • Transaction {app.transaction_id}, Rule {app.rule_id}: {app.warning_message}"
                    )

    def _add_rule_interactive(self) -> None:
        """Add a rule using interactive prompts."""
        print("Interactive rule creation:")
        print("Enter rule details (press Ctrl+C to cancel)")

        try:
            # Get rule ID
            while True:
                try:
                    rule_id = int(input("Rule ID (positive integer): "))
                    if rule_id > 0:
                        break
                    print("Rule ID must be positive")
                except ValueError:
                    print("Please enter a valid integer")

            print("\nRule conditions (at least one required):")

            # Get conditions
            account = input("Account pattern (optional): ").strip() or None
            category = input("Category pattern (optional): ").strip() or None
            merchant = input("Merchant pattern (optional): ").strip() or None

            if not any([account, category, merchant]):
                print(
                    f"{Fore.RED}Error: At least one condition is required{Style.RESET_ALL}"
                )
                return

            print("\nRule transforms (at least one required):")

            # Get transforms
            new_category = input("New category (optional): ").strip() or None
            labels_input = input("Labels (comma-separated, optional): ").strip()
            labels: Optional[List[str]] = (
                [label.strip() for label in labels_input.split(",")]
                if labels_input
                else None
            )
            memo = input("Memo (optional): ").strip() or None

            metadata_input = input(
                "Metadata (key1=value1,key2=value2, optional): "
            ).strip()
            metadata = None
            if metadata_input:
                metadata = {}
                for pair in metadata_input.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        metadata[key.strip()] = value.strip()

            if not any([new_category, labels, memo, metadata]):
                print(
                    f"{Fore.RED}Error: At least one transform is required{Style.RESET_ALL}"
                )
                return

            # Create rule YAML
            rule_yaml = self._create_rule_yaml(
                rule_id,
                account,
                category,
                merchant,
                new_category,
                labels,
                memo,
                metadata,
            )

            print(f"\n{Fore.CYAN}Generated rule:{Style.RESET_ALL}")
            print(rule_yaml)

            # Ask where to save
            output_file = (
                input("\nSave to file (default: rules.yaml): ").strip() or "rules.yaml"
            )

            # Append to file
            with open(output_file, "a", encoding="utf-8") as f:
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    f.write("\n")  # Add newline if file exists and not empty
                f.write(rule_yaml)

            print(f"{Fore.GREEN}Rule added to {output_file}{Style.RESET_ALL}")

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Cancelled{Style.RESET_ALL}")

    def _add_rule_from_args(self, args: argparse.Namespace) -> None:
        """Add a rule from command line arguments."""
        print("Adding rule from command line arguments...")

        # Extract arguments
        rule_id = args.rule_id
        account = args.account
        category = args.category
        merchant = args.merchant
        new_category = args.new_category
        labels = args.labels.split(",") if args.labels else None
        memo = args.memo
        metadata = None

        if args.metadata:
            metadata = {}
            for pair in args.metadata.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    metadata[key.strip()] = value.strip()

        # Validate
        if not any([account, category, merchant]):
            print(
                f"{Fore.RED}Error: At least one condition (--account, --category, --merchant) is required{Style.RESET_ALL}"
            )
            sys.exit(1)

        if not any([new_category, labels, memo, metadata]):
            print(
                f"{Fore.RED}Error: At least one transform (--new-category, --labels, --memo, --metadata) is required{Style.RESET_ALL}"
            )
            sys.exit(1)

        # Create rule YAML
        rule_yaml = self._create_rule_yaml(
            rule_id, account, category, merchant, new_category, labels, memo, metadata
        )

        print(f"\n{Fore.CYAN}Generated rule:{Style.RESET_ALL}")
        print(rule_yaml)

        # Save to file
        output_file = args.output_file or "rules.yaml"

        with open(output_file, "a", encoding="utf-8") as f:
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                f.write("\n")  # Add newline if file exists and not empty
            f.write(rule_yaml)

        print(f"{Fore.GREEN}Rule added to {output_file}{Style.RESET_ALL}")

    def _create_rule_yaml(
        self,
        rule_id: int,
        account: Optional[str],
        category: Optional[str],
        merchant: Optional[str],
        new_category: Optional[str],
        labels: Optional[List[str]],
        memo: Optional[str],
        metadata: Optional[Dict[str, str]],
    ) -> str:
        """Create YAML representation of a rule."""
        lines = [f"- id: {rule_id}"]

        # Add conditions
        lines.append("  if:")
        if account:
            lines.append(f'    - account: "{account}"')
        if category:
            lines.append(f'    - category: "{category}"')
        if merchant:
            lines.append(f'    - merchant: "{merchant}"')

        # Add transforms
        lines.append("  then:")
        if new_category:
            lines.append(f'    - category: "{new_category}"')
        if labels:
            if len(labels) == 1:
                lines.append(f'    - labels: "{labels[0]}"')
            else:
                lines.append("    - labels:")
                for label in labels:
                    lines.append(f"      - {label}")
        if memo:
            lines.append(f'    - memo: "{memo}"')
        if metadata:
            lines.append("    - metadata:")
            for key, value in metadata.items():
                lines.append(f'        {key}: "{value}"')

        return "\n".join(lines)
