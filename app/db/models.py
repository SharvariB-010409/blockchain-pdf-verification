from os import name
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Enum
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

# document status 
class DocumentStatus(str,PyEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    PENDING = "PENDING"
    
# blockchain status
class BlockchainStatus(str,PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"

# documents table
class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    storage_key = Column(String, nullable=True)
    sha256_hash = Column(String, nullable=True, unique=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    document_status = Column(String, nullable = False, default=DocumentStatus.PENDING.value)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    blockchain_transaction_id = Column(String, nullable=True)
    blockchain_block_number = Column(Integer, nullable=True)
    blockchain_status = Column(String, nullable = True, default=BlockchainStatus.PENDING.value)