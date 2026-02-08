import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import analytics, ingestion, students

PORT = int(os.getenv("PORT", 3000))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Student Personalizer API",
    description="API for ingesting and analyzing student data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router)
app.include_router(students.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    return {"message": "Student Personalizer API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
