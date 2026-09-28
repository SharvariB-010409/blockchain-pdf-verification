import os
import uuid
from fastapi import UploadFile

# Directory where uploaded PDFs will be stored
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


class StorageService:
    @staticmethod
    async def save_file(file: UploadFile) -> str:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        return file_path

    @staticmethod
    def delete_file(file_path: str) -> bool:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False