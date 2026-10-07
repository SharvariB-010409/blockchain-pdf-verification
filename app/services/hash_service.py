import hashlib
import io
import logging

from fastapi import UploadFile, HTTPException
from pypdf import PdfReader


logger = logging.getLogger(__name__)


class HashService:
    """
    Computes a content-based SHA-256 hash for a PDF document.
    
    Instead of hashing the raw file bytes or PDF byte structures (which change when 
    saved in WPS Office, Adobe Reader, or Chrome), this class extracts the visual content:
      1. Cleaned text from every page.
      2. Raw bytes of all embedded images on every page.
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit

    @classmethod
    async def validate_and_hash_pdf(cls, file: UploadFile) -> str:
        try:
            # 1. Rewind and read raw bytes
            await file.seek(0)
            file_bytes = await file.read()

            if not file_bytes:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")

            if len(file_bytes) > cls.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail="File size exceeds maximum allowed limit of 10 MB."
                )

            if not file_bytes.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=400, 
                    detail="Uploaded file is not a valid PDF document."
                )

            # 2. Generate content-based hash
            content_hash = cls._calculate_content_hash(file_bytes)

            logger.info("Generated content SHA-256 hash: %s", content_hash)
            return f"sha256:{content_hash}"

        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error processing PDF upload.")
            raise HTTPException(
                status_code=500,
                detail=f"Unable to process PDF: {str(exc)}"
            )

    @classmethod
    def _calculate_content_hash(cls, file_bytes: bytes) -> str:
        """
        Extracts textual content and image payloads page-by-page and hashes them.
        """
        try:
            reader = PdfReader(io.BytesIO(file_bytes), strict=False)
            sha256 = hashlib.sha256()

            for page_index, page in enumerate(reader.pages):
                # --- A. Extract and normalize Text ---
                extracted_text = page.extract_text() or ""
                
                # Strip out whitespace variances (extra spaces/newlines added by editors)
                normalized_text = "".join(extracted_text.split())
                
                # Add text to hash buffer
                sha256.update(f"page_{page_index}_text:".encode("utf-8"))
                sha256.update(normalized_text.encode("utf-8"))

                # --- B. Extract Image Payloads ---
                # Catches logos, signatures, or scanned pages
                if hasattr(page, "images"):
                    for img_index, img in enumerate(page.images):
                        sha256.update(f"page_{page_index}_img_{img_index}:".encode("utf-8"))
                        sha256.update(img.data)

            return sha256.hexdigest()

        except Exception as exc:
            logger.warning("pypdf extraction failed (%s); falling back to direct binary hash.", exc)
            return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    async def hash_pdf_for_verification(cls, file: UploadFile) -> str:
        """
        Guarantees matching verification hash for registration and verification runs.
        """
        return await cls.validate_and_hash_pdf(file)