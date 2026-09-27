import hashlib
import logging

from fastapi import UploadFile, HTTPException, status

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class HashService:

    @staticmethod
    async def validate_and_hash_pdf(file: UploadFile) -> str:

        # Read PDF contents
        contents = await file.read()

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            logger.warning("File size exceeds 10 MB.")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum limit of 10 MB."
            )

        # Check whether file is a PDF
        if not contents.startswith(b"%PDF"):
            logger.warning("File is not a valid PDF.")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid PDF."
            )

        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(contents).hexdigest()

        # Return hash string
        return f"sha256:{sha256_hash}"