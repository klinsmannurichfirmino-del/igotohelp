from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import os
import uuid

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

scripts = {}
tarefas = []
logs = []

@app.get("/")
def home():
    return {"msg": "funcionando"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    filename = file_id + "_" + file.filename
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    scripts[file_id] = file_path

    return {"id": file_id, "nome": file.filename}

@app.get("/scripts")
def get_scripts():
    return scripts

@app.post("/executar/{script_id}")
async def executar(script_id: str):
    if script_id not in scripts:
        return {"erro": "não encontrado"}
    
    caminho = scripts[script_id]
    tarefas.append({
        "id": script_id,
        "caminho": caminho
    })
    
    return {"status": "enviado"}

@app.get("/tarefas")
def get_tarefas():
    result = tarefas.copy()
    tarefas.clear()
    return result

@app.get("/download/{filename}")
async def download(filename: str):
    return FileResponse("uploads/" + filename)

from pydantic import BaseModel

class Resultado(BaseModel):
    script: str
    saida: str
    erro: str

@app.post("/resultado")
async def resultado(result: Resultado):
    logs.append(result.dict())
    return {"ok": True}

@app.get("/logs")
def get_logs():
    return logs
    