import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Document
from app.services.hash_service import HashService
from app.services.blockchain_service import Blockchain 
from app.services.logger import logger
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate PDF and generate SHA-256 hash
        await file.seek(0)

        pdf_hash = await HashService.validate_and_hash_pdf(file)
        
        # Ensure hash starts with "sha256:"
        if not pdf_hash.startswith("sha256:"):
            clean_hash = pdf_hash
            formatted_hash = f"sha256:{pdf_hash}"
        else:
            clean_hash = pdf_hash.replace("sha256:", "")
            formatted_hash = pdf_hash

        # Check whether the document hash already exists in DB
        document_exists = (
            db.query(Document)
            .filter(Document.sha256_hash == formatted_hash)
            .first()
        )

        # If document already exists, return existing record
        if document_exists:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "Document already exists.",
                    "document_id": str(document_exists.id),
                    "record_id": str(document_exists.id),
                    "document_type": document_exists.document_type,
                    "sha256_hash": document_exists.sha256_hash,
                    "blockchain_status": document_exists.blockchain_status,
                    "blockchain_transaction_id": document_exists.blockchain_transaction_id,
                },
            )

        # Generate a unique document ID
        document_id = str(uuid.uuid4())

        # Generate storage key
        storage_key = (
            f"documents/"
            f"{datetime.now().strftime('%Y/%m')}/"
            f"{document_id}/original.pdf"
        )

        # Create document record in DB
        document = Document(
            id=document_id,
            document_type=document_type,
            original_filename=file.filename or "uploaded.pdf",
            storage_key=storage_key,
            sha256_hash=pdf_hash,
            blockchain_status="PENDING"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # Register document on Hyperledger Fabric
        try:
            tx_result = Blockchain.upload_document(
                document_id=str(document.id),
                document_hash=pdf_hash,
                document_type=document_type
            )

            # Update blockchain status in DB
            document.blockchain_status = tx_result.get("blockchain_status", "CONFIRMED")
            document.blockchain_transaction_id = tx_result.get("blockchain_transaction_id")
            document.blockchain_block_number = tx_result.get("blockchain_block_number")

            db.commit()
            db.refresh(document)

        except Exception:
            # Blockchain registration failed.
            db.rollback()

            document = db.query(Document).filter(
                Document.id == document_id
            ).first()

            if document:
                document.blockchain_status = "FAILED"
                db.commit()

            logger.exception(
                "Blockchain registration failed for document %s",
                document_id
            )

            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "success": False,
                    "message": "Document saved, but blockchain registration failed.",
                    "document_id": document_id,
                    "sha256_hash": formatted_hash,
                    "blockchain_status": "FAILED"
                }
            )

        # Return successful response
        return {
                "document_id": str(document.id),
                "record_id": str(document.id),
                "sha256_hash": f"sha256:{document.sha256_hash.replace('sha256:', '')}",
                "blockchain_status": str(document.blockchain_status).lower(), 
                "blockchain_transaction_id": document.blockchain_transaction_id
        }

    except HTTPException:
        # Preserve validation errors from HashService
        raise

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Database error while uploading document")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Database error while uploading document."
            }
        )

    except Exception:
        db.rollback()

        logger.exception("Unexpected error while uploading document")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An unexpected error occurred."
            }
        )

    finally:
        await file.close()
     
     
@router.post("/{document_id}/verify")
async def verify_document(
    document_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try : 
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("Document record not found.")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={"success" : False,
                                    "message" : "Document record not found."})
        
        await file.seek(0)    
        uploaded_hash = await HashService.validate_and_hash_pdf(file)
        hash_matches = (uploaded_hash == document.sha256_hash)

        # Verify 
        ledger_result = Blockchain.verify_document(document_id=str(document.id), document_hash=uploaded_hash)
        record_exists = ledger_result.get("blockchain_record_exists", False)
        chain_hash_matches = ledger_result.get("hash_matches", False)
        block_status = str(
            ledger_result.get("blockchain_status", document.blockchain_status)
        ).upper()
        is_valid_status = block_status in ["CONFIRMED"]
        # Overall verification requires DB hash match, chain hash match, and valid record
        overall_verified = (
            hash_matches and chain_hash_matches and record_exists and is_valid_status
        )
        return {
            "document_id": document.id,
            "record_id" : document.id,
            "verified": overall_verified,
            "hash_matches": hash_matches,
            "blockchain_record_exists": True,
            "blockchain_status" : block_status,
            "blockchain_transaction_id": document.blockchain_transaction_id
    }
    except Exception as e: 
            logger.warning(f"Unhandled Exception: {str(e)}")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                                content={"success" : False, 
                                         "message" : f"Unhandled Exception: {str(e)}"})
            
@router.get("/{document_id}/blockchain")
async def get_blockchain_record(
    document_id: str,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        logger.warning("Document not found !")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={"success" : False, 
                                    "message" : "Document not found !"})
        
    actual_block_number = 1
    for block in Blockchain.chain:
        if (
            isinstance(block.data, dict)
            and block.data.get("document_id") == str(document_id)
        ):
            actual_block_number = block.index
            break

    clean_hash = document.sha256_hash.replace("sha256:", "").lower()
    
    return {
        "record_id": str(document.id),
        "document_hash": f"sha256:{clean_hash}",
        "blockchain_transaction_id": document.blockchain_transaction_id,
        "blokchain_block_number": actual_block_number,
        "status": str(document.blockchain_status).lower()
    }
    
# remove document 
@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = (db.query(Document).filter(Document.id == str(document_id)).first())
    if not document:
        logger.warning("Document not Found")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={"success" : False, 
                                    "message" : "Document not found !"})

    # Delete from PostgreSQL database
    db.delete(document)
    db.commit()

    # Sync removal from in-memory Blockchain
    Blockchain.remove_document(document_id, db)

    return {"success": True, "message": "Document and blockchain record removed"}
   
# get all records of blockchain
@router.get("/blockchain/chain")
async def get_full_blockchain():
    chain_data = []
    for block in Blockchain.chain:
        chain_data.append(
            {
                "index": block.index,
                "timestamp": block.timestamp,
                "data": block.data,
                "previous_hash": block.previous_hash,
                "hash": block.hash,
            }
        )

    return {
        "length": len(chain_data),
        "chain": chain_data,
    }