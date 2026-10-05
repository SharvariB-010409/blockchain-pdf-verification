from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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

# Add CORS Middleware to allow requests from Live Server (port 5500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Live Server origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

# API router - endpoints start with /api/v1/documents
app.include_router(router, prefix="/api/v1/documents", tags=["documents"])

# View UI
@app.get("/", response_class=FileResponse)
async def render_ui():
    html_file = BASE_DIR / "blockchain.html"
    if not html_file.exists():
        raise RuntimeError(f"File not found: {html_file}")
    return FileResponse(html_file)