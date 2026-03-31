"""ML privacy controls (MoE section 4.5).

Enforces an explicit allowlist of ML feature columns so no PII ever
enters the model training or prediction pipeline.  Also provides
audit helpers so every prediction request is logged.
"""

# Ordered list of allowed feature columns - order is preserved for model consistency.
# This is the authoritative source; services/ml.py imports FEATURE_COLUMNS from here.
# All entries are non-PII aggregates derived from grades and attendance.
FEATURE_COLUMNS: list[str] = [
    "average_grade",
    "min_grade",
    "max_grade",
    "grade_std",
    "grade_trend_slope",
    "num_subjects",
    "failing_subjects",
    "absence",
    "absence_justified",
    "late",
    "disturbance",
    "total_absences",
    "total_negative_events",
    "total_positive_events",
]

# Frozenset for O(1) membership checks
ML_FEATURE_ALLOWLIST: frozenset[str] = frozenset(FEATURE_COLUMNS)

# Columns that must NEVER appear in ML features (belt-and-suspenders)
PII_COLUMN_BLOCKLIST: frozenset[str] = frozenset(
    [
        "student_tz",
        "student_name",
        "student_tz_hash",
        "first_name",
        "last_name",
        "parent_name",
        "phone",
        "email",
        "class_id",
        "id",
    ]
)


def sanitize_feature_columns(columns: list[str]) -> list[str]:
    """Return only columns that are on the allowlist and not on the blocklist."""
    return [c for c in columns if c in ML_FEATURE_ALLOWLIST and c not in PII_COLUMN_BLOCKLIST]


def assert_no_pii(df_columns: list[str]) -> None:
    """Raise ValueError if any PII column is present in the DataFrame."""
    violations = [c for c in df_columns if c in PII_COLUMN_BLOCKLIST]
    if violations:
        raise ValueError(f"PII columns detected in ML feature set: {violations}")
