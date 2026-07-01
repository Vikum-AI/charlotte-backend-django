import csv
from datetime import datetime
from pathlib import Path


def read_csv_records(
    path: Path,
    rename: dict | None = None,
    filename: str | None = None,
) -> list[dict]:
    if filename:
        csv_file = path / filename
    else:
        csv_file = next(path.glob('*.csv'))

    with csv_file.open(newline='', encoding='utf-8') as handle:
        records = []
        for row in csv.DictReader(handle):
            record = {}
            for column, value in row.items():
                key = column.lower()
                if rename and key in rename:
                    key = rename[key]
                record[key] = '' if value in (None, '') else value
            records.append(record)
        return records


def parse_float(value) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_string(value) -> str | None:
    if value in (None, ''):
        return None
    return str(value).strip().strip("'").strip('"')


def derive_account_id(dataset: str, customer_id: str, index: int = 1) -> str:
    return f'{dataset}:{customer_id}_acc_{index}'


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def to_iso_timestamp(value: str | None) -> str | None:
    parsed = parse_timestamp(value)
    return parsed.isoformat() if parsed else None
