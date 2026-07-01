from django.core.management.base import BaseCommand

from api.core.backfill.derivations import BACKFILL_FIELDS
from api.core.utils.backfill_transaction_fields import (
    DEFAULT_BATCH_SIZE,
    backfill_transaction_fields,
    dry_run_missing_counts,
)


class Command(BaseCommand):
    help = 'Backfill missing Transaction fields with deterministic synthetic values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report missing field counts without writing',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f'Number of transactions per batch (default: {DEFAULT_BATCH_SIZE})',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        self.stdout.write('Starting transaction field backfill...')
        self.stdout.write(f'Batch size: {batch_size}')

        if dry_run:
            self.stdout.write('Mode: dry-run (no writes)')
            counts = dry_run_missing_counts()
            self.stdout.write('')
            self.stdout.write('Transactions with missing fields:')
            for field_name in BACKFILL_FIELDS:
                self.stdout.write(f'  {field_name}: {counts[field_name]}')
            self.stdout.write('')
            self.stdout.write('Dry-run complete')
            return

        summary = backfill_transaction_fields(batch_size=batch_size)

        self.stdout.write('')
        self.stdout.write(f'Total transactions processed: {summary.total_processed}')
        self.stdout.write('')
        self.stdout.write('Fields backfilled:')
        for field_name in BACKFILL_FIELDS:
            self.stdout.write(f'  {field_name}: {summary.backfilled_per_field[field_name]}')

        self.stdout.write('')
        self.stdout.write('Backfill complete')
