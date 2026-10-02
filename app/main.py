from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.session import engine, Base, SessionLocal
from app.router.documents import router 
from app.services.blockchain_service import Blockchain

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try :
        Blockchain.rebuild_from_db(db)
        Blockchain.sync_pending_documents(db)
    finally : 
        db.close()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router, prefix="/api/v1/documents", tags=["documents"])