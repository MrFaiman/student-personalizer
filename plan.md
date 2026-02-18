Multi-Tenant Architecture with OOP & Decoupling
Context
The app is a single-school student analytics platform with no auth, no tenant concept, and no base classes. Services are manually constructed in routers. This plan adds multi-tenancy (school = tenant), JWT auth, abstract base classes, and dependency injection so the system supports multiple schools with isolated data.

Step 1: Models — School & User + school_id on all tables
File: server/src/models.py

Add two new models:

class School(SQLModel, table=True):
    id: UUID (PK), name: str (unique, indexed), slug: str (unique, indexed), created_at: datetime

class User(SQLModel, table=True):
    id: UUID (PK), email: str (unique, indexed), hashed_password: str,
    full_name: str, role: str ("admin"/"teacher"/"viewer"),
    is_active: bool, school_id: UUID (FK -> school.id), created_at: datetime
Add school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True) to all 6 data tables: Teacher, Class, Student, Grade, AttendanceRecord, ImportLog.

Replace unique=True on Teacher.name and Class.class_name with composite UniqueConstraint("name", "school_id") / UniqueConstraint("class_name", "school_id").

Keep Student.student_tz as PK (Israeli national IDs are globally unique — no collision risk across schools).

Step 2: Auth System
New deps in pyproject.toml: argon2-cffi, python-jose[cryptography]

New constants in server/src/constants.py:

SECRET_KEY, JWT_ALGORITHM = "HS256", ACCESS_TOKEN_EXPIRE_MINUTES = 480
New file: server/src/auth.py

hash_password(), verify_password() (argon2-cffi PasswordHasher)
create_access_token(user_id, school_id) → JWT with sub + school_id claims
get_current_user(token, session) → FastAPI dependency, decodes JWT, returns User
get_current_school_id(user) → convenience dependency, returns UUID
New file: server/src/schemas/auth.py

LoginRequest, TokenResponse, UserResponse, RegisterRequest
New file: server/src/routers/auth.py

POST /api/auth/login — email+password → JWT
GET /api/auth/me — current user info (requires auth)
POST /api/auth/register — create user in caller's school (admin only)
Register auth router in main.py.

Step 3: Seed Default School & Admin
New file: server/src/seed.py

seed_default_school_and_admin(session) — creates default School + admin User if none exist
backfill_school_id(session, school_id) — sets school_id on all existing rows with NULL
Call from lifespan in main.py after init_db().

Step 4: Abstract Base Classes
New file: server/src/services/base.py

class BaseService(ABC):
    def __init__(self, session: Session, school_id: UUID):
        self.session = session
        self.school_id = school_id
New file: server/src/views/base.py

class BaseView(ABC):
    pass
Update all 5 service classes to inherit BaseService and accept (session, school_id). Update all 4 view classes to inherit BaseView.

Step 5: Tenant-Scoped Queries in All Services
Every select() call in every service adds .where(Model.school_id == self.school_id).

Services to update (with school_id filter on every query):

server/src/services/students.py — filter Student, Grade, AttendanceRecord, Class
server/src/services/classes.py — filter Class, Student, Grade
server/src/services/teachers.py — filter Teacher, Grade, Student, Class
server/src/services/analytics.py — filter all tables (largest service, ~870 lines)
server/src/services/ml.py — filter all tables + per-school model file paths (models/{school_id}/) + cache key includes school_id
Convert server/src/services/ingestion.py from module functions to IngestionService(BaseService) class. All get_or_create_* helpers become methods scoped by self.school_id. Stateless helpers (file parsing) stay as module-level functions.

Step 6: Dependency Injection
New file: server/src/dependencies.py

Factory functions for each service, chaining get_session + get_current_school_id:

def get_student_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> StudentService:
    return StudentService(session, school_id)
Same pattern for: get_class_service, get_teacher_service, get_analytics_service, get_ml_service, get_ingestion_service.

Update all routers to use Depends(get_xxx_service) instead of manual construction:

# Before
async def list_students(session: Session = Depends(get_session)):
    service = StudentService(session)

# After
async def list_students(service: StudentService = Depends(get_student_service)):
Routers to update: students.py, classes.py, teachers.py, analytics.py, ml.py, ingestion.py

Auth-exempt routes (no service dependency): /api/auth/login, /health, /, /api/config

Step 7: Reset Endpoint Scoping
The POST /api/ingest/reset endpoint currently drops all tables. Change behavior:

Only delete data for the requesting user's school (not drop tables)
Restrict to admin role
Files Summary
New files (7):
File	Purpose
server/src/auth.py	Argon2 password hashing, JWT, auth dependencies
server/src/seed.py	Default school/admin seeding + backfill
server/src/dependencies.py	DI factory functions for all services
server/src/schemas/auth.py	Auth request/response schemas
server/src/routers/auth.py	Login, register, me endpoints
server/src/services/base.py	BaseService(ABC)
server/src/views/base.py	BaseView(ABC)
Modified files (16):
File	Changes
server/pyproject.toml	Add argon2-cffi, python-jose[cryptography]
server/src/models.py	Add School + User models, school_id FK on all tables, composite unique constraints
server/src/constants.py	Add SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
server/src/main.py	Register auth router, call seed in lifespan
server/src/services/students.py	Inherit BaseService, add school_id filters
server/src/services/classes.py	Inherit BaseService, add school_id filters
server/src/services/teachers.py	Inherit BaseService, add school_id filters
server/src/services/analytics.py	Inherit BaseService, add school_id filters
server/src/services/ml.py	Inherit BaseService, school-scoped model paths + cache
server/src/services/ingestion.py	Convert to IngestionService class, add school_id scoping
server/src/routers/students.py	Use DI Depends
server/src/routers/classes.py	Use DI Depends
server/src/routers/teachers.py	Use DI Depends
server/src/routers/analytics.py	Use DI Depends
server/src/routers/ml.py	Use DI Depends
server/src/routers/ingestion.py	Use DI Depends, use IngestionService
Verification
uv run ruff check . — no lint errors
Start server: uv run server — app boots, tables created, default school + admin seeded
POST /api/auth/login with admin@school.local / admin123 → get JWT
All existing endpoints work with Authorization: Bearer <token> header
Create a second school + user, import data for each — verify data isolation (school A cannot see school B's students)
Unauthenticated requests to protected endpoints return 401

---

## 1. Security: The "Forgot the Where Clause" Risk

The biggest risk in shared-database multi-tenancy is a developer forgetting `.where(Model.school_id == self.school_id)` in a new query.

* **Improvement:** If you are using SQLAlchemy (which SQLModel wraps), look into **Global Search Filters**. You can configure the `Session` or use an event listener to automatically append the `school_id` filter to every select query based on the `self.school_id` in your context.
* **Alternative:** If you stick to manual filters, create a helper method in `BaseService`:
```python
def scoped_select(self, model):
    return select(model).where(model.school_id == self.school_id)

```


This makes it easier to do the right thing than the wrong thing.

## 2. The `Student.student_tz` Exception

You mentioned keeping the Israeli ID as a PK because it's "globally unique."

* **The Risk:** While the ID is unique to a person, what if two different schools try to "claim" the same student record? Or what if a student moves from School A to School B?
* **Recommendation:** Even if the ID is unique, include `school_id` in the primary key (Composite PK) or at least keep the `school_id` column. If a student exists in two schools, you likely want two distinct records for their grades/attendance specific to that institution.

## 3. Middleware for `school_id`

Right now, you’re extracting `school_id` in a dependency. That’s great for services.

* **Improvement:** Consider adding a small **FastAPI Middleware** or a `ContextVar`. This allows you to access the `current_school_id` anywhere in the execution chain (like logging or background tasks) without passing it through five layers of function arguments.

## 4. The `seed.py` Strategy

Your plan to backfill `school_id` on existing rows is critical.

* **Improvement:** Ensure your `backfill_school_id` runs inside a **transaction**. If the migration fails halfway through, you don't want a "half-tenanted" database where some data is orphaned and some is assigned.
* **Validation:** Add a `CheckConstraint` or a `Nullable=False` on `school_id` *after* the backfill is complete to ensure no "homeless" data ever enters the system again.

## 5. ML Model Isolation (Step 5)

You mentioned `models/{school_id}/`.

* **Watch out for:** Path traversal. Ensure that when you construct these paths, you validate the `school_id` is a valid UUID and not a string like `../../etc/`. Using the `UUID` type in your `BaseService` handles this naturally, but keep it in mind for the file system operations.

## 6. Updated File Summary & Edge Cases

| Area | Suggested Tweaks |
| --- | --- |
| **Migrations** | Use **Alembic**. Manually adding columns to a live DB is risky. Alembic handles the `ADD COLUMN` and `DEFAULT` logic cleanly. |
| **Role-Based Access** | You have roles ("admin", "teacher"). Ensure your `get_current_user` dependency can also check for specific roles (e.g., `RoleChecker(["admin"])`). |
| **Caching** | Since you're using `school_id` in cache keys, ensure your cache eviction policy clears *only* that school's data when an update happens. |

---

### One Final Thought: The "Super Admin"

You'll eventually need a way to see *all* schools (for your own support/debugging). Your current plan locks every query to a `school_id`.

* **Next Step:** Would you like me to show you how to structure a `User` role that can bypass the `school_id` filter for a "Global Dashboard" view?