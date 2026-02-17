from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .constants import PORT, ORIGIN_URL, API_DESCRIPTION, API_TITLE, API_VERSION, DEFAULT_ORIGIN_URL, DEFAULT_PORT
from .database import init_db
from .routers import advanced_analytics, analytics, config, ingestion, ml, students



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
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
app.include_router(config.router)
app.include_router(ingestion.router)
app.include_router(students.router)
app.include_router(analytics.router)
app.include_router(advanced_analytics.router)
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
