from src.services.sql_join_guard import SQLJoinGuard


def test_join_guard_accepts_allowed_join():
    guard = SQLJoinGuard()
    constraints = {
        "required_table_names": ["orders", "customers"],
        "allowed_edges": [
            {
                "primary_table_name": "orders",
                "primary_field_name": "customer_id",
                "foreign_table_name": "customers",
                "foreign_field_name": "id",
            }
        ],
    }
    sql = """
    SELECT o.id, c.name
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    """

    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is True


def test_join_guard_rejects_unconfigured_join():
    guard = SQLJoinGuard()
    constraints = {
        "required_table_names": ["orders", "customers"],
        "allowed_edges": [
            {
                "primary_table_name": "orders",
                "primary_field_name": "customer_id",
                "foreign_table_name": "customers",
                "foreign_field_name": "id",
            }
        ],
    }
    sql = """
    SELECT o.id, c.name
    FROM orders o
    JOIN customers c ON o.id = c.id
    """

    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is False
    assert result.error_code == "JOIN_GUARD_INVALID_EDGE"


def test_join_guard_rejects_missing_required_table():
    guard = SQLJoinGuard()
    constraints = {
        "required_table_names": ["orders", "customers"],
        "allowed_edges": [],
    }
    sql = "SELECT * FROM orders"

    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is False
    assert result.error_code == "JOIN_GUARD_MISSING_REQUIRED_TABLES"


def test_join_guard_accepts_inferred_candidate_join():
    guard = SQLJoinGuard()
    constraints = {
        "mode": "inferred",
        "required_table_names": ["orders", "customers"],
        "allowed_edges": [],
        "inferred_candidates": [
            {
                "primary_table_name": "orders",
                "primary_field_name": "customer_id",
                "foreign_table_name": "customers",
                "foreign_field_name": "id",
                "score": 0.88,
                "reason": "field_name_exact_match,id_pattern_match",
            }
        ],
    }
    sql = """
    SELECT o.id, c.name
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    """
    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is True


def test_join_guard_allows_cte_join_alias_with_strict_edges():
    guard = SQLJoinGuard()
    constraints = {
        "mode": "strict",
        "required_table_names": ["survey_attendance_mock", "fiscal_calendar_holidays", "park_seasonal_campaign"],
        "allowed_edges": [
            {
                "primary_table_name": "survey_attendance_mock",
                "primary_field_name": "FY_N",
                "foreign_table_name": "fiscal_calendar_holidays",
                "foreign_field_name": "fiscal_year_number",
            },
            {
                "primary_table_name": "survey_attendance_mock",
                "primary_field_name": "FW_N",
                "foreign_table_name": "fiscal_calendar_holidays",
                "foreign_field_name": "fiscal_week_number",
            },
        ],
    }
    sql = """
    WITH target_weeks AS (
      SELECT DISTINCT f.fiscal_year_number AS FY_N, f.fiscal_week_number AS FW_N
      FROM fiscal_calendar_holidays f
      JOIN park_seasonal_campaign c
        ON f.calendar_date BETWEEN c.campaign_start_date AND c.campaign_end_date
      WHERE c.campaign_name LIKE '%奇奇蒂蒂生日月%'
    )
    SELECT SUM(s.ATTN)
    FROM target_weeks tw
    JOIN survey_attendance_mock s
      ON tw.FY_N = s.FY_N AND tw.FW_N = s.FW_N
    """
    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is True


def test_join_guard_allows_inline_subquery_join_alias_with_strict_edges():
    """JOIN (SELECT ...) vw ON s.FY_N = vw.FY_N 应与 WITH tw AS (...) 一样通过守卫。"""
    guard = SQLJoinGuard()
    constraints = {
        "mode": "strict",
        "required_table_names": ["survey_attendance_mock", "fiscal_calendar_holidays", "park_seasonal_campaign"],
        "allowed_edges": [
            {
                "primary_table_name": "survey_attendance_mock",
                "primary_field_name": "FY_N",
                "foreign_table_name": "fiscal_calendar_holidays",
                "foreign_field_name": "fiscal_year_number",
            },
            {
                "primary_table_name": "survey_attendance_mock",
                "primary_field_name": "FW_N",
                "foreign_table_name": "fiscal_calendar_holidays",
                "foreign_field_name": "fiscal_week_number",
            },
        ],
    }
    sql = """
    SELECT SUM(s.ATTN)
    FROM survey_attendance_mock s
    JOIN (
      SELECT DISTINCT f.fiscal_year_number AS FY_N, f.fiscal_week_number AS FW_N
      FROM fiscal_calendar_holidays f
      JOIN park_seasonal_campaign c
        ON f.calendar_date BETWEEN c.campaign_start_date AND c.campaign_end_date
      WHERE c.campaign_name LIKE '%奇奇蒂蒂生日月%'
    ) vw ON s.FY_N = vw.FY_N AND s.FW_N = vw.FW_N
    """
    result = guard.validate_sql(sql=sql, join_constraints=constraints, db_type="mysql")
    assert result.is_valid is True
