import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from src.core.config import settings
from src.api import repurpose
from src.db.session import engine
from src.models.content import Base
from src.middleware.session import SessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENV == "dev":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield  
    await engine.dispose()  

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API to repurpose YouTube videos into Blogs and Social Posts.",
    version="1.0.0",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware)

app.include_router(repurpose.router, prefix="/api/v1", tags=["Repurpose"])


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}