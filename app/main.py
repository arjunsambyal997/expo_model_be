from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, ideas, users
from app.core.config import settings
from app.db import Base, engine
from app.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables directly. Switch to Alembic migrations before production.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.seed_demo_data:
        await seed()
    yield


app = FastAPI(title="Idea Board API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth.router, users.router, ideas.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
