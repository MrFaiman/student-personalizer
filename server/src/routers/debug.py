"""
Debug router - only for development/testing.
Provides an endpoint to seed the database with generated dummy data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from ..constants import XLSX_CONTENT_TYPE
from ..database import get_session
from ..services.data_generator import generate_school_data
from ..services.ingestion import IngestionService

router = APIRouter(prefix="/api/debug", tags=["debug"])


class FileResult(BaseModel):
    filename: str
    file_type: str
    period: str
    year: str
    rows_imported: int
    rows_failed: int
    students_created: int
    classes_created: int


class GenerateResponse(BaseModel):
    files_processed: int
    total_rows_imported: int
    total_rows_failed: int
    total_students_created: int
    total_classes_created: int
    results: list[FileResult]


@router.post("/generate", response_model=GenerateResponse)
def generate_debug_data(
    years: Annotated[list[int], Query()] = [2024, 2025],
    quarters: Annotated[int, Query(ge=1, le=4)] = 4,
    students: Annotated[int, Query(ge=1, le=500)] = 120,
    db: Session = Depends(get_session),
) -> GenerateResponse:
    """
    Generate and ingest dummy school data directly into the database.
    Each call regenerates the same deterministic dataset (seed=42).
    """
    files = generate_school_data(years=list(years), quarters=quarters, num_students=students)

    service = IngestionService(db)
    results: list[FileResult] = []

    for filename, content, file_type, period, year in files:
        result = service.ingest_file(
            file_content=content,
            filename=filename,
            content_type=XLSX_CONTENT_TYPE,
            file_type=file_type,
            period=period,
            year=year,
        )
        results.append(FileResult(
            filename=filename,
            file_type=file_type,
            period=period,
            year=year,
            rows_imported=result.rows_imported,
            rows_failed=result.rows_failed,
            students_created=result.students_created,
            classes_created=result.classes_created,
        ))

    return GenerateResponse(
        files_processed=len(results),
        total_rows_imported=sum(r.rows_imported for r in results),
        total_rows_failed=sum(r.rows_failed for r in results),
        total_students_created=sum(r.students_created for r in results),
        total_classes_created=sum(r.classes_created for r in results),
        results=results,
    )
