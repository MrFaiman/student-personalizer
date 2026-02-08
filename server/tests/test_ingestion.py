"""
Test script for XLSX ingestion API using files from /data directory.

Usage:
1. Start the server: uv run uvicorn main:app --reload
2. Run this script: uv run python test_ingestion.py
"""

import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:3000"
DATA_DIR = Path(__file__).parent.parent / "data"


def check_server():
    """Check if the server is running."""
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except httpx.ConnectError:
        return False


def test_upload_grades():
    """Test uploading grades file via API."""
    print("\n" + "=" * 60)
    print("Testing Grades File Upload")
    print("=" * 60)

    grades_file = DATA_DIR / "avg_grades.xlsx"
    if not grades_file.exists():
        print(f"ERROR: File not found: {grades_file}")
        return None

    with open(grades_file, "rb") as f:
        files = {"file": ("avg_grades.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        params = {"period": "Semester 1", "file_type": "grades"}

        response = httpx.post(
            f"{BASE_URL}/api/ingest/upload",
            files=files,
            params=params,
            timeout=60,
        )

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Batch ID: {data['batch_id']}")
        print(f"File type: {data['file_type']}")
        print(f"Rows imported: {data['rows_imported']}")
        print(f"Rows failed: {data['rows_failed']}")
        print(f"Students created: {data['students_created']}")
        print(f"Classes created: {data['classes_created']}")

        if data.get("errors"):
            print(f"\nFirst 5 errors:")
            for err in data["errors"][:5]:
                print(f"  - {err}")

        return data["batch_id"]
    else:
        print(f"Error: {response.text}")
        return None


def test_upload_events():
    """Test uploading events file via API."""
    print("\n" + "=" * 60)
    print("Testing Events/Attendance File Upload")
    print("=" * 60)

    events_file = DATA_DIR / "events.xlsx"
    if not events_file.exists():
        print(f"ERROR: File not found: {events_file}")
        return None

    with open(events_file, "rb") as f:
        files = {"file": ("events.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        params = {"period": "Semester 1", "file_type": "events"}

        response = httpx.post(
            f"{BASE_URL}/api/ingest/upload",
            files=files,
            params=params,
            timeout=60,
        )

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Batch ID: {data['batch_id']}")
        print(f"File type: {data['file_type']}")
        print(f"Rows imported: {data['rows_imported']}")
        print(f"Rows failed: {data['rows_failed']}")
        print(f"Students created: {data['students_created']}")
        print(f"Classes created: {data['classes_created']}")

        if data.get("errors"):
            print(f"\nFirst 5 errors:")
            for err in data["errors"][:5]:
                print(f"  - {err}")

        return data["batch_id"]
    else:
        print(f"Error: {response.text}")
        return None


def test_auto_detection():
    """Test auto-detection of file types."""
    print("\n" + "=" * 60)
    print("Testing Auto-Detection (no file_type param)")
    print("=" * 60)

    for filename in ["avg_grades.xlsx", "events.xlsx"]:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"Skipping {filename} - not found")
            continue

        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            params = {"period": "Auto-Detect Test"}

            response = httpx.post(
                f"{BASE_URL}/api/ingest/upload",
                files=files,
                params=params,
                timeout=60,
            )

        if response.status_code == 200:
            data = response.json()
            print(f"\n{filename}:")
            print(f"  Detected type: {data['file_type']}")
            print(f"  Rows imported: {data['rows_imported']}")
        else:
            print(f"\n{filename}: Error - {response.text}")


def test_get_students():
    """Test fetching students via API."""
    print("\n" + "=" * 60)
    print("Testing GET /api/students")
    print("=" * 60)

    response = httpx.get(f"{BASE_URL}/api/students", params={"page_size": 5}, timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total students: {data['total']}")
        print(f"Page: {data['page']}")
        print(f"\nSample students:")
        for student in data["items"][:5]:
            risk = " [AT RISK]" if student["is_at_risk"] else ""
            avg = student["average_grade"] or "N/A"
            print(f"  - {student['student_name']} ({student['class_name']}): avg={avg}{risk}")
    else:
        print(f"Error: {response.text}")


def test_get_dashboard():
    """Test fetching dashboard stats via API."""
    print("\n" + "=" * 60)
    print("Testing GET /api/students/dashboard")
    print("=" * 60)

    response = httpx.get(f"{BASE_URL}/api/students/dashboard", timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nDashboard Stats:")
        print(f"  Total students: {data['total_students']}")
        print(f"  Average grade: {data['average_grade']}")
        print(f"  At-risk count: {data['at_risk_count']}")
        print(f"  Total classes: {data['total_classes']}")

        print(f"\nClasses:")
        for cls in data["classes"][:5]:
            print(f"  - {cls['class_name']}: {cls['student_count']} students, avg={cls['average_grade']}, at-risk={cls['at_risk_count']}")
    else:
        print(f"Error: {response.text}")


def test_get_classes():
    """Test fetching classes via API."""
    print("\n" + "=" * 60)
    print("Testing GET /api/students/classes")
    print("=" * 60)

    response = httpx.get(f"{BASE_URL}/api/students/classes", timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nClasses ({len(data)} total):")
        for cls in data:
            print(f"  - {cls['class_name']} (Grade {cls['grade_level']}): {cls['student_count']} students")
    else:
        print(f"Error: {response.text}")


def test_get_import_logs():
    """Test fetching import logs via API."""
    print("\n" + "=" * 60)
    print("Testing GET /api/ingest/logs")
    print("=" * 60)

    response = httpx.get(f"{BASE_URL}/api/ingest/logs", timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nImport logs ({len(data)} total):")
        for log in data[:5]:
            print(f"  - {log['filename']}: {log['rows_imported']} imported, {log['rows_failed']} failed ({log['file_type']})")
    else:
        print(f"Error: {response.text}")


def main():
    print("=" * 60)
    print("XLSX Ingestion API Test Client")
    print("=" * 60)

    print(f"\nServer: {BASE_URL}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Files found: {[f.name for f in DATA_DIR.glob('*.xlsx')]}")

    # Check if server is running
    if not check_server():
        print("\nERROR: Server is not running!")
        print("Start the server with: uv run uvicorn main:app --reload")
        sys.exit(1)

    print("\nServer is running!")

    # Run tests
    test_upload_grades()
    test_upload_events()
    test_get_students()
    test_get_dashboard()
    test_get_classes()
    test_get_import_logs()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
