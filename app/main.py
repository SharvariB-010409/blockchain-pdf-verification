from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db.session import engine, Base, SessionLocal
from app.router.documents import router 
from app.services.blockchain_service import Blockchain

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        Blockchain.rebuild_from_db(db)
        Blockchain.sync_pending_documents(db)
    finally:
        db.close()
    yield

app = FastAPI(lifespan=lifespan)

# api router
app.include_router(router, prefix="/api/v1/documents", tags=["documents"])

# view blockchain ui
@app.get("/", response_class=FileResponse)
async def render_ui():
    html_file = BASE_DIR / "blockchain.html"
    if not html_file.exists():
        raise RuntimeError(f"File not found: {html_file}")
    return FileResponse(html_file)