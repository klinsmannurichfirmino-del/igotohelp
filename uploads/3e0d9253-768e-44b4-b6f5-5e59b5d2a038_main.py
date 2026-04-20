from fastapi import FastAPI, UploadFile, File
import os
import uuid

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# guardar scripts
scripts = {}

@app.get("/")
def home():
    return {"msg": "funcionando"}

# upload de arquivo
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, file_id + "_" + file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    scripts[file_id] = file_path

    return {"id": file_id, "nome": file.filename}
