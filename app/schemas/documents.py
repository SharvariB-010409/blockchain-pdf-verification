from uuid import UUID
from pydantic import BaseModel, Field

# create / upload document
class DocumentUpload(BaseModel):
    document_id: str = Field(..., example="doc_123")
    record_id: str = Field(..., example="rec_123")
    sha256_hash: str = Field(..., example="sha256:8f72a4...")
    blockchain_status: str = Field(..., example="confirmed")
    blockchain_transaction_id: str = Field(..., example="fabric-tx-123")

# verify document
class DocumentVerify(BaseModel):
    document_id: str = Field(..., example="doc_123")
    record_id: str = Field(..., example="rec_123")
    verified: bool = Field(..., example=True)
    hash_matches: bool = Field(..., example=True)
    blockchain_record_exists: bool = Field(..., example=True)
    blockchain_transaction_id: str = Field(..., example="fabric-tx-123")

# response model for blockchain record
class BlockchainRecord(BaseModel):
    record_id: str = Field(..., example="rec_123")
    document_hash: str = Field(..., example="sha256:8f72a4...")
    blockchain_transaction_id: str = Field(..., example="fabric-tx-123")
    block_number: int = Field(..., example=42)
    status: str = Field(..., example="confirmed")