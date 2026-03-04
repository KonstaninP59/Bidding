import os
import shutil
from fastapi import UploadFile
from uuid import uuid4

UPLOAD_DIR = "uploads"

def save_upload_file(upload_file: UploadFile, subfolder: str = "common") -> str:
    """
    Сохраняет загруженный файл на диск и возвращает путь к нему.
    Имя файла заменяется на UUID, чтобы избежать дубликатов и проблем с кириллицей.
    """
    # Создаем папку, если нет
    directory = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(directory, exist_ok=True)
    
    # Генерируем уникальное имя
    extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid4()}{extension}"
    file_path = os.path.join(directory, unique_filename)
    
    # Сохраняем
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return file_path
