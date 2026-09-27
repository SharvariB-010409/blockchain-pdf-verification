import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

# generate a record_id when a new document is created
def generate_record_id():
    return str(uuid.uuid4())

# documents table
class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_record_id)
    document_type = Column(String, nullable=False)
    original_filename = Column(String)
    storage_key = Column(String)
    sha256_hash = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    blockchain_transaction_id = Column(String)
    blockchain_block_number = Column(Integer)
    blockchain_status = Column(String)