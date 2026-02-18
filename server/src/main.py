from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .constants import API_DESCRIPTION, API_TITLE, API_VERSION, ORIGIN_URL, PORT
from .database import get_session_context, init_db
from .routers import analytics, classes, config, ingestion, ml, students, teachers
from .routers.auth import router as auth_router
from .seed import backfill_school_id, seed_default_school_and_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, seed default school & admin."""
    init_db()
    with get_session_context() as session:
        school_id = seed_default_school_and_admin(session)
        backfill_school_id(session, school_id)
    yield


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGIN_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(config.router)
app.include_router(ingestion.router)
app.include_router(classes.router)
app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(analytics.router)

app.include_router(ml.router)


@app.get("/")
async def root():
    return {"message": API_TITLE}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
