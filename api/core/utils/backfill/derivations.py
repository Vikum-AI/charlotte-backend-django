import hashlib
from datetime import datetime, timedelta, timezone

TIMESTAMP_BASE = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
FIVE_YEARS_SECONDS = 5 * 365 * 24 * 60 * 60  # 157_680_000

CURRENCY_CHOICES = (('USD', 60), ('EUR', 20), ('GBP', 10), ('AUD', 10))
STATUS_CHOICES = (
    ('COMPLETED', 80),
    ('PENDING', 10),
    ('FLAGGED', 7),
    ('REVERSED', 3),
)
CHANNEL_CHOICES = (('card', 45), ('ach', 25), ('wire', 20), ('mobile', 10))
CATEGORY_CHOICES = (
    ('payment', 40),
    ('transfer', 30),
    ('deposit', 15),
    ('withdrawal', 15),
)
TYPE_CHOICES = (('debit', 55), ('credit', 45))


def _digest_hex(transaction_id: str) -> str:
    return hashlib.sha256(transaction_id.encode()).hexdigest()


def _weighted_choice(
    transaction_id: str,
    hex_offset: int,
    choices: list[tuple[str, int]],
) -> str:
    n = int(_digest_hex(transaction_id)[hex_offset:hex_offset + 8], 16)
    total = sum(weight for _, weight in choices)
    bucket = n % total
    cumulative = 0
    for value, weight in choices:
        cumulative += weight
        if bucket < cumulative:
            return value
    return choices[-1][0]


def derive_currency(transaction_id: str) -> str:
    return _weighted_choice(transaction_id, 0, list(CURRENCY_CHOICES))


def derive_status(transaction_id: str) -> str:
    return _weighted_choice(transaction_id, 8, list(STATUS_CHOICES))


def derive_channel(transaction_id: str) -> str:
    return _weighted_choice(transaction_id, 16, list(CHANNEL_CHOICES))


def derive_category(transaction_id: str) -> str:
    return _weighted_choice(transaction_id, 24, list(CATEGORY_CHOICES))


def derive_type(transaction_id: str) -> str:
    return _weighted_choice(transaction_id, 32, list(TYPE_CHOICES))


def derive_timestamp_iso(transaction_id: str) -> str:
    offset_seconds = int(_digest_hex(transaction_id)[40:48], 16) % FIVE_YEARS_SECONDS
    ts = TIMESTAMP_BASE + timedelta(seconds=offset_seconds)
    return ts.strftime('%Y-%m-%dT%H:%M:%SZ')


DERIVE_BY_FIELD = {
    'currency': derive_currency,
    'timestamp': derive_timestamp_iso,
    'status': derive_status,
    'channel': derive_channel,
    'category': derive_category,
    'type': derive_type,
}

BACKFILL_FIELDS = tuple(DERIVE_BY_FIELD.keys())
