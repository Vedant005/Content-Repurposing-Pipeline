import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api import repurpose
from src.db.session import engine
from src.models.content import Base
from src.middleware.session import SessionMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API to repurpose YouTube videos into Blogs and Social Posts.",
    version="1.0.0"
)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware)

@app.on_event("startup")
async def startup():
    
    if os.getenv("ENV", "dev") == "dev":
        async with engine.begin() as conn:

            await conn.run_sync(Base.metadata.create_all)
            print("--- DB Tables Created (Dev Mode) ---")

app.include_router(repurpose.router, prefix="/api/v1", tags=["Repurpose"])

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}