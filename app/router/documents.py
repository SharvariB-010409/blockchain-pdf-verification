from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.db.models import Document
from app.services.hash_service import HashService
from app.services.blockchain_service import Blockchain


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    tags=["Documents"]
)


# ============================================================
# GET ALL DOCUMENTS
# ============================================================

@router.get("")
async def get_documents(
    db: Session = Depends(get_db)
):
    try:
        documents = (
            db.query(Document)
            .order_by(Document.created_at.desc())
            .all()
        )

        result = []

        for document in documents:
            result.append({
                "document_id": str(document.id),
                "document_type": document.document_type,
                "original_filename": document.original_filename,
                "sha256_hash": document.sha256_hash,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "document_status": document.status,
                "blockchain_status": document.blockchain_status,
                "blockchain_transaction_id": (
                    document.blockchain_transaction_id
                ),
                "blockchain_block_number": (
                    document.blockchain_block_number
                ),
                "created_at": document.created_at,
                "updated_at": document.updated_at
            })

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load documents: {str(exc)}"
        )


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # ------------------------------------------------------
        # 1. Validate PDF + generate normalized hash
        # ------------------------------------------------------

        document_hash = await HashService.validate_and_hash_pdf(file)

        # ------------------------------------------------------
        # 2. Check duplicate document
        # ------------------------------------------------------

        existing_document = (
            db.query(Document)
            .filter(Document.sha256_hash == document_hash)
            .first()
        )

        if existing_document:
            return {
                "message": "Document already exists.",
                "document_id": str(existing_document.id),
                "original_filename": (
                    existing_document.original_filename
                ),
                "document_type": existing_document.document_type,
                "sha256_hash": existing_document.sha256_hash,
                "document_status": existing_document.status,
                "blockchain_status": (
                    existing_document.blockchain_status
                ),
                "blockchain_transaction_id": (
                    existing_document.blockchain_transaction_id
                ),
                "blockchain_block_number": (
                    existing_document.blockchain_block_number
                )
            }

        # ------------------------------------------------------
        # 3. Read original file
        # ------------------------------------------------------

        await file.seek(0)

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        # ------------------------------------------------------
        # 4. Create database record
        # ------------------------------------------------------

        document = Document(
            document_type=document_type,
            original_filename=file.filename,
            storage_key=file.filename,
            sha256_hash=document_hash,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            status="ACTIVE",
            blockchain_status="PENDING"
        )

        db.add(document)

        db.commit()

        db.refresh(document)

        # ------------------------------------------------------
        # 5. Add document hash to blockchain
        # ------------------------------------------------------

        blockchain_result = await Blockchain.add_document(
            document_id=str(document.id),
            document_hash=document_hash,
            document_type=document_type
        )

        # ------------------------------------------------------
        # 6. Update blockchain information
        # ------------------------------------------------------

        if blockchain_result:

            document.blockchain_status = blockchain_result.get(
                "status",
                "CONFIRMED"
            )

            document.blockchain_transaction_id = (
                blockchain_result.get("transaction_id")
            )

            document.blockchain_block_number = (
                blockchain_result.get("block_number")
            )

            db.commit()

            db.refresh(document)

        # ------------------------------------------------------
        # 7. Return response
        # ------------------------------------------------------

        return {
            "message": "Document uploaded successfully.",
            "document_id": str(document.id),
            "original_filename": document.original_filename,
            "document_type": document.document_type,
            "sha256_hash": document.sha256_hash,
            "document_status": document.status,
            "blockchain_status": document.blockchain_status,
            "blockchain_transaction_id": (
                document.blockchain_transaction_id
            ),
            "blockchain_block_number": (
                document.blockchain_block_number
            )
        }

    except HTTPException:
        raise

    except SQLAlchemyError as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(exc)}"
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(exc)}"
        )


# ============================================================
# VERIFY DOCUMENT
# ============================================================

@router.post("/verify")
async def verify_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # ------------------------------------------------------
        # 1. Generate SAME normalized hash
        # ------------------------------------------------------

        uploaded_hash = (
            await HashService.hash_pdf_for_verification(file)
        )

        # ------------------------------------------------------
        # 2. Find document using hash
        # ------------------------------------------------------

        document = (
            db.query(Document)
            .filter(Document.sha256_hash == uploaded_hash)
            .first()
        )

        # ------------------------------------------------------
        # 3. Hash does not exist
        # ------------------------------------------------------

        if not document:

            return {
                "verified": False,
                "message": "Document verification failed.",
                "sha256_hash": uploaded_hash
            }

        # ------------------------------------------------------
        # 4. Check document status
        # ------------------------------------------------------

        if document.status == "REVOKED":

            return {
                "verified": False,
                "message": "Document has been revoked.",
                "document_id": str(document.id),
                "sha256_hash": uploaded_hash,
                "document_status": document.status,
                "blockchain_status": (
                    document.blockchain_status
                ),
                "blockchain_transaction_id": (
                    document.blockchain_transaction_id
                ),
                "blockchain_block_number": (
                    document.blockchain_block_number
                )
            }

        # ------------------------------------------------------
        # 5. Check blockchain status
        # ------------------------------------------------------

        if document.blockchain_status != "CONFIRMED":

            return {
                "verified": False,
                "message": (
                    "Document hash exists, but blockchain "
                    "confirmation is not complete."
                ),
                "document_id": str(document.id),
                "sha256_hash": uploaded_hash,
                "document_status": document.status,
                "blockchain_status": (
                    document.blockchain_status
                ),
                "blockchain_transaction_id": (
                    document.blockchain_transaction_id
                ),
                "blockchain_block_number": (
                    document.blockchain_block_number
                )
            }

        # ------------------------------------------------------
        # 6. SUCCESS
        # ------------------------------------------------------

        return {
            "verified": True,
            "message": "Document verified successfully.",
            "document_id": str(document.id),
            "sha256_hash": uploaded_hash,
            "document_status": document.status,
            "blockchain_status": (
                document.blockchain_status
            ),
            "blockchain_transaction_id": (
                document.blockchain_transaction_id
            ),
            "blockchain_block_number": (
                document.blockchain_block_number
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(exc)}"
        )


# ============================================================
# GET SINGLE DOCUMENT
# ============================================================

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    try:

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        # ------------------------------------------------------
        # Document not found
        # ------------------------------------------------------

        if not document:

            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

        # ------------------------------------------------------
        # Return document
        # ------------------------------------------------------

        return {
            "document_id": str(document.id),
            "document_type": document.document_type,
            "original_filename": document.original_filename,
            "storage_key": document.storage_key,
            "sha256_hash": document.sha256_hash,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "document_status": document.status,
            "blockchain_status": (
                document.blockchain_status
            ),
            "blockchain_transaction_id": (
                document.blockchain_transaction_id
            ),
            "blockchain_block_number": (
                document.blockchain_block_number
            ),
            "created_at": document.created_at,
            "updated_at": document.updated_at
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(exc)}"
        )