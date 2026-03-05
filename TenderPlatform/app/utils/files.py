import os
import shutil
from fastapi import UploadFile, HTTPException
from uuid import uuid4
from app.config import settings


async def validate_file(file: UploadFile):
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"Файл слишком большой. Максимум {settings.MAX_FILE_SIZE} байт")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Тип файла {ext} не разрешён")


async def save_upload_file(upload_file: UploadFile, subfolder: str = "common") -> str:
    directory = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(directory, exist_ok=True)
    extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid4()}{extension}"
    file_path = os.path.join(directory, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path
