import os
from typing import Optional


DEFAULT_SQL_SERVER_DRIVER = "ODBC Driver 18 for SQL Server"


def _escape_odbc_value(value: str) -> str:
    """
    Escape ODBC connection string value with braces.

    This prevents delimiter conflicts for values containing ';' or '}'.
    """
    return "{" + value.replace("}", "}}") + "}"


def _pick_sql_server_driver(preferred_driver: str) -> str:
    """Select an available SQL Server ODBC driver, with fallback."""
    try:
        import pyodbc  # type: ignore

        installed = pyodbc.drivers()
        if preferred_driver in installed:
            return preferred_driver
        if "ODBC Driver 18 for SQL Server" in installed:
            return "ODBC Driver 18 for SQL Server"
        if "ODBC Driver 17 for SQL Server" in installed:
            return "ODBC Driver 17 for SQL Server"
    except Exception:
        # If pyodbc is unavailable or probing fails, keep preferred value.
        pass
    return preferred_driver


def build_sql_server_connection_string(
    host: str,
    port: int,
    database_name: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    domain: Optional[str] = None,
) -> str:
    """
    Build SQL Server ODBC connection string with TLS settings.

    Environment variables:
    - ODBC_DRIVER (default: ODBC Driver 18 for SQL Server)
    - ODBC_ENCRYPT (default: yes)
    - ODBC_TRUST_SERVER_CERTIFICATE (default: no)
    - ODBC_HOSTNAME_IN_CERTIFICATE (optional)
    """
    preferred_driver = os.getenv("ODBC_DRIVER", DEFAULT_SQL_SERVER_DRIVER)
    driver = _pick_sql_server_driver(preferred_driver)
    encrypt = os.getenv("ODBC_ENCRYPT", "yes")
    trust_server_certificate = os.getenv("ODBC_TRUST_SERVER_CERTIFICATE", "no")
    hostname_in_certificate = os.getenv("ODBC_HOSTNAME_IN_CERTIFICATE", "").strip()

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={host},{port}",
        f"DATABASE={database_name}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_server_certificate}",
    ]

    if hostname_in_certificate:
        parts.append(f"HostNameInCertificate={hostname_in_certificate}")

    if domain:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={_escape_odbc_value(username or '')}")
        parts.append(f"PWD={_escape_odbc_value(password or '')}")

    return ";".join(parts) + ";"
