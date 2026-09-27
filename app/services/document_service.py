from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import status, Depends
from app.db.models import Document
from app.db.session import get_db
from app.services.logger import logger
from app.schemas.documents import DocumentCreate, DocumentUpdate, DocumentResponse

# create / upload document
def create_document(document: DocumentCreate, db: Session = Depends(get_db)):
    try : 
        document_exists = db.query(Document).filter(Document.sha256_hash == document.sha256_hash).first()
        if document_exists:
            logger.warning(f"Document with SHA-256 hash {document.sha256_hash} already exists in the database.")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                                content={"success" : False,
                                        "message": "Document already exists in the database."})
        db_document = Document(**document.dict())
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return JSONResponse(status_code=status.HTTP_201_CREATED, 
                            content={"success" : True,
                                     "message": "Document created successfully.",
                                     "data": db_document})
    
    except Exception as e:
        logger.error(f"An unexpected error occured while creating document: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            content={"success" : False,
                                     "message": "An unexpected error occurred while creating the document."})

# get all documents
def get_all_documents(db: Session = Depends(get_db)):
    try:
        db_documents = db.query(Document).all()
        return JSONResponse(status_code=status.HTTP_200_OK, 
                            content={"success" : True,
                                     "message": "Documents retrieved successfully.",
                                     "data": db_documents})
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving documents: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            content={"success" : False,
                                     "message": "An unexpected error occurred while retrieving the documents."})

# get document by id
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    try:
        db_document = db.query(Document).filter(Document.id == document_id).first()
        if not db_document:
            logger.warning(f"Document with ID {document_id} not found in the database.")
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, 
                                content={"success" : False,
                                         "message": "Document not found in the database."})
        return JSONResponse(status_code=status.HTTP_200_OK, 
                            content={"success" : True,
                                     "message": "Document retrieved successfully.",
                                     "data": db_document})
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving document: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            content={"success" : False,
                                     "message": "An unexpected error occurred while retrieving the document."})

# update document        
def update_document(document_id: UUID, document: DocumentUpdate, db: Session = Depends(get_db)):
    try:
        db_document = db.query(Document).filter(Document.id == document_id).first()
        if not db_document:
            logger.warning(f"Document with ID {document_id} not found in the database.")
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, 
                                content={"success" : False,
                                         "message": "Document not found in the database."})
        
        for key, value in document.dict(exclude_unset=True).items():
            setattr(db_document, key, value)
        
        db.commit()
        db.refresh(db_document)
        return JSONResponse(status_code=status.HTTP_200_OK, 
                            content={"success" : True,
                                     "message": "Document updated successfully.",
                                     "data": db_document})
    
    except Exception as e:
        logger.error(f"An unexpected error occured while updating document: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            content={"success" : False,
                                     "message": "An unexpected error occurred while updating the document."})
        
# remove document
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    try:
        db_document = db.query(Document).filter(Document.id == document_id).first()
        if not db_document:
            logger.warning(f"Document with ID {document_id} not found in the database.")
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, 
                                content={"success" : False,
                                         "message": "Document not found in the database."})
        
        db.delete(db_document)
        db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, 
                            content={"success" : True,
                                     "message": "Document deleted successfully."})
    
    except Exception as e:
        logger.error(f"An unexpected error occured while deleting document: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            content={"success" : False,
                                     "message": "An unexpected error occurred while deleting the document."})  
        