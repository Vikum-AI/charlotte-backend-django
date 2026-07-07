from django.core.management.base import BaseCommand, CommandError
from neomodel import db


VALIDATE_TRANSACTIONS_QUERY = """
UNWIND $ids AS transaction_id
OPTIONAL MATCH (t:Transaction {transaction_id: transaction_id})
RETURN transaction_id, t IS NOT NULL AS exists
"""

RESET_DEMO_FEATURED_QUERY = """
MATCH (t:Transaction)
WHERE coalesce(t.is_demo_featured, false) = true
  AND NOT t.transaction_id IN $ids
SET t.is_demo_featured = false
RETURN count(t)
"""

MARK_DEMO_FEATURED_QUERY = """
MATCH (t:Transaction)
WHERE t.transaction_id IN $ids
SET t.is_demo_featured = true
RETURN count(t)
"""


class Command(BaseCommand):
    help = 'Mark selected Transaction nodes as featured for the demo transaction picker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            required=True,
            help='Comma-separated transaction IDs to mark as demo featured',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Unset demo featured flag on transactions not included in --ids',
        )

    def handle(self, *args, **options):
        ids = _parse_ids(options['ids'])
        reset = options['reset']

        if not ids:
            raise CommandError('At least one transaction ID is required')

        missing_ids = _missing_transaction_ids(ids)
        if missing_ids:
            raise CommandError(
                f"Transaction IDs not found: {', '.join(missing_ids)}",
            )

        self.stdout.write('Marking demo featured transactions...')
        self.stdout.write(f"Transaction IDs: {', '.join(ids)}")

        reset_count = 0
        if reset:
            reset_results, _ = db.cypher_query(RESET_DEMO_FEATURED_QUERY, {'ids': ids})
            reset_count = reset_results[0][0] if reset_results else 0
            self.stdout.write(
                f'Reset demo featured flag on {reset_count} transactions',
            )

        marked_results, _ = db.cypher_query(MARK_DEMO_FEATURED_QUERY, {'ids': ids})
        marked_count = marked_results[0][0] if marked_results else 0

        self.stdout.write(f'Marked {marked_count} demo featured transactions')
        self.stdout.write('Demo transaction marking complete')


def _parse_ids(raw_ids: str) -> list[str]:
    ids = [transaction_id.strip() for transaction_id in raw_ids.split(',')]
    return list(dict.fromkeys(transaction_id for transaction_id in ids if transaction_id))


def _missing_transaction_ids(ids: list[str]) -> list[str]:
    results, _ = db.cypher_query(VALIDATE_TRANSACTIONS_QUERY, {'ids': ids})
    existing_by_id = {row[0]: row[1] for row in results}
    return [transaction_id for transaction_id in ids if not existing_by_id[transaction_id]]
