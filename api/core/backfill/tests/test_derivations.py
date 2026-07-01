from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from api.core.backfill.derivations import (
    CATEGORY_CHOICES,
    CHANNEL_CHOICES,
    CURRENCY_CHOICES,
    FIVE_YEARS_SECONDS,
    STATUS_CHOICES,
    TIMESTAMP_BASE,
    TYPE_CHOICES,
    derive_category,
    derive_channel,
    derive_currency,
    derive_status,
    derive_timestamp_iso,
    derive_type,
)

GOLDEN_CASES = {
    'txn_001': {
        'currency': 'GBP',
        'status': 'COMPLETED',
        'channel': 'wire',
        'category': 'deposit',
        'type': 'debit',
        'timestamp': '2022-12-05T05:09:54Z',
    },
    'banksim_123_1_0': {
        'currency': 'EUR',
        'status': 'COMPLETED',
        'channel': 'card',
        'category': 'transfer',
        'type': 'debit',
        'timestamp': '2023-03-03T20:42:00Z',
    },
    'amlsim_456': {
        'currency': 'USD',
        'status': 'COMPLETED',
        'channel': 'card',
        'category': 'payment',
        'type': 'debit',
        'timestamp': '2022-02-12T16:54:53Z',
    },
}

DERIVERS = {
    'currency': (derive_currency, {value for value, _ in CURRENCY_CHOICES}),
    'status': (derive_status, {value for value, _ in STATUS_CHOICES}),
    'channel': (derive_channel, {value for value, _ in CHANNEL_CHOICES}),
    'category': (derive_category, {value for value, _ in CATEGORY_CHOICES}),
    'type': (derive_type, {value for value, _ in TYPE_CHOICES}),
}


class DerivationTests(SimpleTestCase):
    def test_determinism(self):
        transaction_id = 'txn_deterministic_42'
        for derive_fn, _ in DERIVERS.values():
            self.assertEqual(derive_fn(transaction_id), derive_fn(transaction_id))
        self.assertEqual(
            derive_timestamp_iso(transaction_id),
            derive_timestamp_iso(transaction_id),
        )

    def test_golden_values(self):
        for transaction_id, expected in GOLDEN_CASES.items():
            self.assertEqual(derive_currency(transaction_id), expected['currency'])
            self.assertEqual(derive_status(transaction_id), expected['status'])
            self.assertEqual(derive_channel(transaction_id), expected['channel'])
            self.assertEqual(derive_category(transaction_id), expected['category'])
            self.assertEqual(derive_type(transaction_id), expected['type'])
            self.assertEqual(derive_timestamp_iso(transaction_id), expected['timestamp'])

    def test_return_values_are_from_allowed_sets(self):
        transaction_id = 'txn_allowed_values'
        for derive_fn, allowed in DERIVERS.values():
            self.assertIn(derive_fn(transaction_id), allowed)

    def test_timestamp_within_five_year_range(self):
        transaction_ids = [f'txn_ts_{index}' for index in range(200)]
        upper_bound = TIMESTAMP_BASE + timedelta(seconds=FIVE_YEARS_SECONDS)

        for transaction_id in transaction_ids:
            parsed = datetime.strptime(
                derive_timestamp_iso(transaction_id),
                '%Y-%m-%dT%H:%M:%SZ',
            ).replace(tzinfo=timezone.utc)
            self.assertGreaterEqual(parsed, TIMESTAMP_BASE)
            self.assertLess(parsed, upper_bound)

    def test_fields_are_decoupled_for_fixed_id(self):
        transaction_id = 'txn_decouple_check'
        values = {
            derive_currency(transaction_id),
            derive_status(transaction_id),
            derive_channel(transaction_id),
            derive_category(transaction_id),
            derive_type(transaction_id),
            derive_timestamp_iso(transaction_id),
        }
        self.assertGreaterEqual(len(values), 3)

    def test_status_weight_distribution(self):
        sample_size = 1000
        completed_count = sum(
            1
            for index in range(sample_size)
            if derive_status(f'status_weight_{index}') == 'COMPLETED'
        )
        completed_share = completed_count / sample_size
        self.assertGreaterEqual(completed_share, 0.70)
        self.assertLessEqual(completed_share, 0.90)
