from pydantic import BaseModel
from typing import Optional

class BlockchainUploadRequest(BaseModel) :
    document_id : str
    document_hash: str
    document_hash :str

class BlockchainUploadResponse(BaseModel):
    blockchain_status : str
    blockchain_transaction_id : str

class BlockchainVerifyResponse(BaseModel):
    verfied : str
    blockchain_transaction_id : Optional[str]=None