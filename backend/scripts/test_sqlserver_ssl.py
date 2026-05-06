#!/usr/bin/env python3
"""
SQL Server SSL/TLS connectivity diagnostic script.

Usage example:
  uv run python scripts/test_sqlserver_ssl.py \
    --host your-sqlserver-host \
    --port 1433 \
    --database your_database \
    --username your_user \
    --password your_password
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure "src" can be imported when script runs from backend/scripts
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.utils.sql_server_odbc import build_sql_server_connection_string  # noqa: E402


def _load_env_file(env_path: Path) -> None:
    """Load .env key-value pairs into process environment if missing."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _mask_connection_string(connection_string: str) -> str:
    """Hide password in printed connection string."""
    start = connection_string.find("PWD=")
    if start == -1:
        return connection_string

    value_start = start + len("PWD=")
    i = value_start
    in_braces = i < len(connection_string) and connection_string[i] == "{"

    if in_braces:
        i += 1
        while i < len(connection_string):
            ch = connection_string[i]
            if ch == "}":
                # Escaped right brace in ODBC is "}}"
                if i + 1 < len(connection_string) and connection_string[i + 1] == "}":
                    i += 2
                    continue
                i += 1
                break
            i += 1
    else:
        while i < len(connection_string) and connection_string[i] != ";":
            i += 1

    # Consume the field separator ';' if present.
    if i < len(connection_string) and connection_string[i] == ";":
        i += 1

    return connection_string[:start] + "PWD=******;" + connection_string[i:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test SQL Server SSL connection by pyodbc")
    parser.add_argument("--host", required=True, help="SQL Server host")
    parser.add_argument("--port", type=int, default=1433, help="SQL Server port (default: 1433)")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--timeout", type=int, default=10, help="Connection timeout in seconds")
    return parser.parse_args()


def main() -> int:
    _load_env_file(BACKEND_ROOT / ".env")
    args = parse_args()

    try:
        import pyodbc  # type: ignore
    except ModuleNotFoundError:
        print("FAIL: pyodbc not installed")
        return 2

    print("=== SQL Server SSL Diagnostic ===")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Database: {args.database}")
    print(f"ODBC drivers: {pyodbc.drivers()}")
    print(f"ODBC_DRIVER={os.getenv('ODBC_DRIVER', '')}")
    print(f"ODBC_ENCRYPT={os.getenv('ODBC_ENCRYPT', '')}")
    print(f"ODBC_TRUST_SERVER_CERTIFICATE={os.getenv('ODBC_TRUST_SERVER_CERTIFICATE', '')}")
    print(f"ODBC_HOSTNAME_IN_CERTIFICATE={os.getenv('ODBC_HOSTNAME_IN_CERTIFICATE', '')}")

    connection_string = build_sql_server_connection_string(
        host=args.host,
        port=args.port,
        database_name=args.database,
        username=args.username,
        password=args.password,
        domain=None,
    )
    print(f"ConnectionString: {_mask_connection_string(connection_string)}")

    start_time = time.time()
    try:
        conn = pyodbc.connect(connection_string, timeout=args.timeout)
        elapsed_ms = int((time.time() - start_time) * 1000)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version_row = cursor.fetchone()
        version_text = version_row[0] if version_row else "UNKNOWN"
        cursor.close()
        conn.close()
        print(f"SUCCESS: Connected in {elapsed_ms} ms")
        print(f"ServerVersion: {version_text}")
        return 0
    except pyodbc.Error as exc:
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"FAIL: pyodbc.Error after {elapsed_ms} ms")
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"FAIL: unexpected exception after {elapsed_ms} ms")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
