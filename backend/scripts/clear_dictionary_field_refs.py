#!/usr/bin/env python3
"""
Clear table-field references to a dictionary.

Use this when frontend cannot remove dictionary references.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import SessionLocal  # noqa: E402
from src.models.data_preparation_model import Dictionary, TableField, DataTable  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clear table-field dictionary references")
    parser.add_argument("--dict-id", help="Dictionary ID")
    parser.add_argument("--dict-code", help="Dictionary code, e.g. order_status")
    parser.add_argument("--dict-name", help="Dictionary name, e.g. 订单状态")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run only)",
    )
    return parser.parse_args()


def resolve_dictionary(db, dict_id: str | None, dict_code: str | None, dict_name: str | None):
    query = db.query(Dictionary)
    if dict_id:
        return query.filter(Dictionary.id == dict_id).first()
    if dict_code:
        return query.filter(Dictionary.code == dict_code).first()
    if dict_name:
        return query.filter(Dictionary.name == dict_name).first()
    return None


def main() -> int:
    args = parse_args()
    if not any([args.dict_id, args.dict_code, args.dict_name]):
        print("ERROR: Please provide one of --dict-id / --dict-code / --dict-name")
        return 2

    db = SessionLocal()
    try:
        dictionary = resolve_dictionary(db, args.dict_id, args.dict_code, args.dict_name)
        if not dictionary:
            print("ERROR: Dictionary not found")
            return 1

        refs = (
            db.query(TableField, DataTable)
            .join(DataTable, TableField.table_id == DataTable.id)
            .filter(TableField.dictionary_id == dictionary.id)
            .order_by(DataTable.table_name, TableField.field_name)
            .all()
        )

        print(f"Dictionary: {dictionary.name} ({dictionary.code})")
        print(f"Dictionary ID: {dictionary.id}")
        print(f"References found: {len(refs)}")
        for field, table in refs:
            print(f"- {table.table_name}.{field.field_name} (field_id={field.id})")

        if not args.apply:
            print("Dry-run only. Re-run with --apply to clear references.")
            return 0

        for field, _table in refs:
            field.dictionary_id = None

        db.commit()
        print(f"Done. Cleared {len(refs)} reference(s).")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
