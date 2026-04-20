from pydantic import BaseModel
from typing import dict
import os
import uuid

APP_UPLOAD_DIR = "uploads/apps"
os.makedirs(APP_UPLOAD_DIR, exist_ok=True)

APP_ALLOWED_EXTS = {'.exe', '.msi', '.zip'}
MAX_APP_SIZE = 50 * 1024 * 1024  # 50MB

class AppUploadRequest(BaseModel):
    nome: str
    descricao: str
    categoria: str = "utilidades"

def is_app_allowed(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in APP_ALLOWED_EXTS)

def create_app(id: str, nome: str, categoria: str, descricao: str, path: str, uploader: str) -> dict:
    return {
        "id": id, "nome": nome, "categoria": categoria, "descricao": descricao, "arquivo": path, 
        "status": "pending", "downloads": 0, "rating": 0.0, "avaliacoes": 0, "comments": [], "uploader": uploader
    }
