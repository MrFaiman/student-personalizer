import os

from dotenv import load_dotenv

load_dotenv()

# Server
DEFAULT_PORT = 3000
PORT = int(os.getenv("PORT", DEFAULT_PORT))

DEFAULT_ORIGIN_URL = "http://localhost:5173"
ORIGIN_URL = os.getenv("ORIGIN_URL", DEFAULT_ORIGIN_URL)

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/student_personalizer"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

API_TITLE = "Student Personalizer API"
API_DESCRIPTION = "API for ingesting and analyzing student data"
API_VERSION = "0.1.0"

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# Grade thresholds
AT_RISK_GRADE_THRESHOLD = 55
MEDIUM_GRADE_UPPER_BOUND = 75
GOOD_GRADE_UPPER_BOUND = 90

# Display thresholds
MEDIUM_GRADE_THRESHOLD = 70
GOOD_GRADE_THRESHOLD = 80
EXCELLENT_GRADE_THRESHOLD = 85
PERFORMANCE_GOOD_THRESHOLD = 70
PERFORMANCE_MEDIUM_THRESHOLD = 40
GRADE_RANGE_MIN = 0
GRADE_RANGE_MAX = 100

# Performance score weights
GRADE_WEIGHT = 0.60
ATTENDANCE_WEIGHT = 0.25
BEHAVIOR_WEIGHT = 0.15
ATTENDANCE_WEIGHT_NO_GRADES = 0.625
BEHAVIOR_WEIGHT_NO_GRADES = 0.375

# ML
MIN_TRAINING_SAMPLES = 5
HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.3
CROSS_VALIDATION_FOLDS = 5

# Ingestion
MAX_ERRORS_IN_RESPONSE = 20
MAX_STORED_ERRORS = 100
VALID_MIME_TYPES = {
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    "application/vnd.ms-excel": "excel",
}
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DEFAULT_PERIOD = "Default"
DEFAULT_YEAR = ""
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "").lower() in ("1", "true", "yes")

# Auth (MoE section 4.1)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_HOURS = int(os.getenv("REFRESH_TOKEN_EXPIRE_HOURS", "8"))
INACTIVITY_TIMEOUT_MINUTES = int(os.getenv("INACTIVITY_TIMEOUT_MINUTES", "30"))

# Development bypass, set AUTH_REQUIRED=false to skip auth enforcement during development
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() not in ("0", "false", "no")
