"""FastAPI 入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.config import ensure_dirs, settings
from backend.routers import consult, literature


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    db.init_db()
    yield


app = FastAPI(title="星语 ASD RAG API", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(literature.router)
app.include_router(consult.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
