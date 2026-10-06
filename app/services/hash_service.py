import hashlib
import io
import logging

from fastapi import UploadFile, HTTPException
from pypdf import PdfReader, PdfWriter


logger = logging.getLogger(__name__)


class HashService:
    """
    Creates a stable SHA-256 hash for a PDF.

    IMPORTANT:
    We do NOT hash the original PDF bytes directly.

    A PDF can contain changing metadata such as:
        - CreationDate
        - ModDate
        - Producer
        - Creator
        - internal PDF object information

    Two visually identical PDFs can therefore have different
    raw SHA-256 hashes.

    To avoid that problem, we rebuild the PDF without metadata
    and calculate the hash of that normalized PDF.
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    @staticmethod
    async def validate_and_hash_pdf(file: UploadFile) -> str:
        """
        Validate PDF and generate a normalized SHA-256 hash.

        This is used when uploading/registering a document.
        """

        try:
            # ---------------------------------------------------------
            # Read file
            # ---------------------------------------------------------
            await file.seek(0)
            file_bytes = await file.read()

            # ---------------------------------------------------------
            # Check empty file
            # ---------------------------------------------------------
            if not file_bytes:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty."
                )

            # ---------------------------------------------------------
            # Check file size
            # ---------------------------------------------------------
            if len(file_bytes) > HashService.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="PDF file size must not exceed 10 MB."
                )

            # ---------------------------------------------------------
            # Check PDF signature
            # PDF files normally start with %PDF
            # ---------------------------------------------------------
            if not file_bytes.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is not a valid PDF."
                )

            # ---------------------------------------------------------
            # Generate normalized hash
            # ---------------------------------------------------------
            pdf_hash = HashService._calculate_normalized_hash(file_bytes)

            logger.info(
                "Normalized PDF SHA-256 generated: %s",
                pdf_hash
            )

            return f"sha256:{pdf_hash}"

        except HTTPException:
            raise

        except Exception as exc:
            logger.exception("Error while hashing PDF")

            raise HTTPException(
                status_code=400,
                detail=f"Unable to process PDF: {str(exc)}"
            )

    @staticmethod
    def _calculate_normalized_hash(file_bytes: bytes) -> str:
        """
        Remove PDF metadata and create a stable PDF representation,
        then calculate SHA-256.
        """

        try:
            # ---------------------------------------------------------
            # Read original PDF
            # ---------------------------------------------------------
            reader = PdfReader(io.BytesIO(file_bytes))

            # ---------------------------------------------------------
            # Create a new PDF
            # ---------------------------------------------------------
            writer = PdfWriter()

            # Copy every page
            for page in reader.pages:
                writer.add_page(page)

            # ---------------------------------------------------------
            # VERY IMPORTANT:
            # Do not copy the original metadata.
            #
            # We intentionally create the normalized PDF without
            # CreationDate, ModDate, Producer, Creator, etc.
            # ---------------------------------------------------------
            writer.add_metadata({})

            # ---------------------------------------------------------
            # Write normalized PDF to memory
            # ---------------------------------------------------------
            normalized_pdf = io.BytesIO()

            writer.write(normalized_pdf)

            normalized_bytes = normalized_pdf.getvalue()

            # ---------------------------------------------------------
            # SHA-256
            # ---------------------------------------------------------
            sha256 = hashlib.sha256()
            sha256.update(normalized_bytes)

            return sha256.hexdigest()

        except Exception as exc:
            logger.exception("Failed to normalize PDF")

            raise ValueError(
                f"Could not normalize PDF: {str(exc)}"
            )

    @staticmethod
    async def hash_pdf_for_verification(file: UploadFile) -> str:
        """
        Generate the SAME normalized hash during verification.

        This MUST use exactly the same logic as registration.
        """

        return await HashService.validate_and_hash_pdf(file)