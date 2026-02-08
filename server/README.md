# Student Personalizer API

REST API for ingesting and analyzing student academic data. Built with FastAPI, SQLModel, and Pandas.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run server
```

The API starts on `http://localhost:3000` by default. Set the `PORT` environment variable to change it.

### Docker

```bash
docker build -t student-personalizer-api .
docker run -p 3000:3000 student-personalizer-api
```

## Configuration

| Variable       | Default                | Description       |
| -------------- | ---------------------- | ----------------- |
| `PORT`         | `3000`                 | Server port       |
| `DATABASE_URL` | `sqlite:///./data.db`  | Database URL      |

## Database Models

### Class

| Column       | Type   | Description                        |
| ------------ | ------ | ---------------------------------- |
| `class_name` | str PK | Class identifier (e.g. "י-1")     |
| `grade_level`| str    | Grade level (e.g. "10", "י")      |

### Student

| Column        | Type   | Description                        |
| ------------- | ------ | ---------------------------------- |
| `student_tz`  | str PK | Student ID (ת.ז)                  |
| `student_name`| str    | Full name                          |
| `class_name`  | str FK | References `Class.class_name`      |

### Grade

| Column        | Type       | Description                    |
| ------------- | ---------- | ------------------------------ |
| `id`          | int PK     | Auto-generated                 |
| `student_tz`  | str FK     | References `Student.student_tz`|
| `subject`     | str        | Subject name                   |
| `teacher_name`| str \| None| Teacher name                   |
| `grade`       | float      | Numeric grade                  |
| `period`      | str        | Academic period                |

### AttendanceRecord

| Column                 | Type   | Description                     |
| ---------------------- | ------ | ------------------------------- |
| `id`                   | int PK | Auto-generated                  |
| `student_tz`           | str FK | References `Student.student_tz` |
| `absence`              | int    | Unexcused absences              |
| `absence_justified`    | int    | Excused absences                |
| `late`                 | int    | Late arrivals                   |
| `disturbance`          | int    | Disturbance events              |
| `total_absences`       | int    | Sum of all absence types        |
| `total_negative_events`| int    | Sum of all negative events      |
| `total_positive_events`| int    | Sum of all positive events      |
| `period`               | str    | Academic period                 |

### ImportLog

| Column         | Type          | Description                      |
| -------------- | ------------- | -------------------------------- |
| `id`           | int PK        | Auto-generated                   |
| `batch_id`     | str           | Unique import batch identifier   |
| `filename`     | str           | Original filename                |
| `file_type`    | str           | `"grades"` or `"events"`        |
| `rows_imported`| int           | Successfully imported rows       |
| `rows_failed`  | int           | Failed rows                      |
| `errors`       | str \| None   | JSON-encoded error details       |
| `period`       | str \| None   | Academic period                  |
| `created_at`   | datetime      | Import timestamp                 |

## API Endpoints

### General

| Method | Path      | Description        |
| ------ | --------- | ------------------ |
| GET    | `/`       | API info           |
| GET    | `/health` | Health check       |

### Ingestion `/api/ingest`

| Method | Path               | Description                  |
| ------ | ------------------ | ---------------------------- |
| POST   | `/upload`          | Upload and ingest XLSX file  |
| GET    | `/logs`            | List import history          |
| GET    | `/logs/{batch_id}` | Get import batch details     |

**POST `/api/ingest/upload`**

Accepts multipart form data:

| Field       | Type           | Description                                          |
| ----------- | -------------- | ---------------------------------------------------- |
| `file`      | UploadFile     | `.xlsx` file                                         |
| `file_type` | str (optional) | `"grades"` or `"events"` (auto-detected if omitted)  |
| `period`    | str (optional) | Academic period (default `"Default"`)                |

Returns `ImportResponse` with `batch_id`, row counts, and any errors.

### Students `/api/students`

| Method | Path                        | Description                  |
| ------ | --------------------------- | ---------------------------- |
| GET    | `/`                         | List students (paginated)    |
| GET    | `/dashboard`                | Dashboard statistics         |
| GET    | `/classes`                  | List classes with stats      |
| GET    | `/{student_tz}`             | Student detail               |
| GET    | `/{student_tz}/grades`      | Student grades               |
| GET    | `/{student_tz}/attendance`  | Student attendance records   |

**Query parameters for `GET /api/students/`:**

| Param          | Type | Default | Description                     |
| -------------- | ---- | ------- | ------------------------------- |
| `page`         | int  | 1       | Page number                     |
| `page_size`    | int  | 20      | Items per page (max 100)        |
| `class_name`   | str  | —       | Filter by class                 |
| `search`       | str  | —       | Search by student name          |
| `at_risk_only` | bool | false   | Only students with avg < 55     |
| `period`       | str  | —       | Filter by academic period       |

### Analytics `/api/analytics`

| Method | Path                               | Description                      |
| ------ | ---------------------------------- | -------------------------------- |
| GET    | `/kpis`                            | Grade-level KPIs                 |
| GET    | `/class-comparison`                | Class average comparison         |
| GET    | `/class/{class_name}/heatmap`      | Student x subject grade matrix   |
| GET    | `/class/{class_name}/rankings`     | Top/bottom students in a class   |
| GET    | `/teacher/{teacher_name}/stats`    | Teacher grade distribution       |
| GET    | `/student/{student_tz}/radar`      | Student subject grades (radar)   |
| GET    | `/teachers`                        | List all teachers                |
| GET    | `/metadata`                        | Available periods, levels, etc.  |

**Common query parameters:**

| Param        | Type | Description                  |
| ------------ | ---- | ---------------------------- |
| `period`     | str  | Filter by academic period    |
| `grade_level`| str  | Filter by grade level        |

**`GET /class/{class_name}/rankings` additional params:**

| Param      | Type | Default | Description               |
| ---------- | ---- | ------- | ------------------------- |
| `top_n`    | int  | 5       | Number of top students    |
| `bottom_n` | int  | 5       | Number of bottom students |

## File Format

The ingestion service accepts `.xlsx` files with Hebrew column headers. File type is auto-detected based on columns present.

**Grades files** are expected to have columns like `ת.ז` (ID), `שם התלמיד` (name), `שכבה` (grade level), `כיתה` (class number), followed by subject columns in `"Subject - Teacher"` format.

**Events/attendance files** are expected to have columns like `ת.ז. התלמיד` (student ID), `שיעורים שדווחו` (reported lessons), `חיסור` (absence), and various behavioral event columns.

## Testing

```bash
# Start the server first
uv run server

# Run tests
pytest tests/ -v
```

