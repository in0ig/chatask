from src.services.sql_dialect_guard import SQLDialectGuard


def test_sqlserver_rejects_limit():
    guard = SQLDialectGuard()
    sql = "SELECT * FROM t LIMIT 10"
    result = guard.validate_sql(sql, db_type="SQL Server")
    assert result.is_valid is False
    assert result.error_code == "DIALECT_GUARD_MISMATCH"


def test_mysql_rejects_top():
    guard = SQLDialectGuard()
    sql = "SELECT TOP 10 * FROM t"
    result = guard.validate_sql(sql, db_type="mysql")
    assert result.is_valid is False
    assert result.error_code == "DIALECT_GUARD_MISMATCH"


def test_mysql_accepts_limit():
    guard = SQLDialectGuard()
    sql = "SELECT * FROM t LIMIT 10"
    result = guard.validate_sql(sql, db_type="mysql")
    assert result.is_valid is True


def test_sqlserver_accepts_top():
    guard = SQLDialectGuard()
    sql = "SELECT TOP 10 * FROM t ORDER BY id DESC"
    result = guard.validate_sql(sql, db_type="sqlserver")
    assert result.is_valid is True
