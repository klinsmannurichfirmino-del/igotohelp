from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Header, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from backend.services.apps import APP_UPLOAD_DIR, APP_ALLOWED_EXTS, AppUploadRequest, is_app_allowed, create_app
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import uuid
import jwt
import hashlib
from datetime import datetime, timedelta
import threading
import time
import subprocess
import tempfile

app = FastAPI(title="iGoToHelp SaaS", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

UPLOAD_DIR = "uploads"
SANDBOX_DIR = "sandbox"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SANDBOX_DIR, exist_ok=True)

ALLOWED_EXTS = {'.py', '.bat', '.ps1'}

class UploadRequest(BaseModel):
    nome: str
    categoria: str
    descricao: str
    publico: bool = True

class Resultado(BaseModel):
    script: str
    saida: str
    erro: str
    device: str

class Avaliacao(BaseModel):
    nota: int

class Register(BaseModel):
    username: str
    password: str

class Login(BaseModel):
    username: str
    password: str

class Device(BaseModel):
    id: str
    nome: str

class Status(BaseModel):
    cpu: float
    ram: float
    disk: float
    device: str

class Regra(BaseModel):
    device: str
    tipo: str
    limite: float
    script_id: str

class Agendamento(BaseModel):
    script_id: str
    device: str
    intervalo: int

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Data with owner
users = {}
scripts: dict[str, dict] = {}
tarefas: List[dict] = []
logs: dict[str, List[dict]] = defaultdict(list)  # user -> logs
favoritos: dict[str, List[str]] = defaultdict(list)
devices = {}
status_devices = {}
regras = []
agendamentos = []
connection_manager = set()

apps: Dict[str, dict] = {}
packs: Dict[str, dict] = {}

def create_script(id: str, nome: str, categoria: str, descricao: str, path: str, owner: str, publico: bool) -> dict:
    return {
        "id": id, "nome": nome, "categoria": categoria, "descricao": descricao,
        "path": path, "owner": owner, "publico": publico,
        "execucoes": 0, "rating": 0.0, "avaliacoes": 0
    }

def is_allowed_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTS)

@app.post("/register")
async def register(user: Register):
    if user.username in users:
        raise HTTPException(400, "Usuário existe")
    pwd_hash = hashlib.sha256(user.password.encode()).hexdigest()
    users[user.username] = {"password": pwd_hash}
    token = jwt.encode({"sub": user.username, "exp": datetime.utcnow() + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token}

@app.post("/login")
async def login(user: Login):
    if user.username not in users:
        raise HTTPException(401, "Usuário não encontrado")
    pwd_hash = hashlib.sha256(user.password.encode()).hexdigest()
    if users[user.username]["password"] != pwd_hash:
        raise HTTPException(401, "Senha incorreta")
    token = jwt.encode({"sub": user.username, "exp": datetime.utcnow() + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token}

@app.post("/upload", dependencies=[Depends(get_current_user)])
async def upload(
    file: UploadFile = File(...),
    request: UploadRequest = Depends(),
    authorization: str = Header(None)
):
    if not is_allowed_file(file.filename):
        raise HTTPException(400, "Tipo de arquivo não permitido")
    
    file_id = str(uuid.uuid4())
    filename = file_id + "_" + file.filename
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    username = jwt.decode(authorization.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    script = create_script(file_id, request.nome, request.categoria, request.descricao, file_path, username, request.publico)
    scripts[file_id] = script
    return {"id": file_id, "script": script}

@app.post("/apps/executar/{app_id}", dependencies=[Depends(get_current_user)])
async def executar_app(app_id: str, current_user: str = Depends(get_current_user)):
    if app_id not in apps or apps[app_id]["status"] != "approved":
        raise HTTPException(403, "App not approved")
    device_id = request.query_params.get('device_id')
    if not device_id:
        raise HTTPException(400, "device_id required")
    tarefas.append({
        "type": "app",
        "id": app_id,
        "device_id": device_id,
        "path": apps[app_id]["arquivo"]
    })
    return {"status": "sent"}

@app.post("/apps/upload", dependencies=[Depends(get_current_user)])
async def upload_app(
    file: UploadFile = File(...),
    request: AppUploadRequest = Depends(),
    authorization: str = Header(None)
):
    if not request.nome or len(request.nome) > 100:
        raise HTTPException(400, "Nome inválido")
    if len(request.categoria) > 50:
        raise HTTPException(400, "Categoria inválida")
    if not is_app_allowed(file.filename):
        raise HTTPException(400, "Extensão não permitida (.exe .msi .zip)")
    
    contents = await file.read()
    if len(contents) > MAX_APP_SIZE:
        raise HTTPException(400, "Arquivo muito grande (max 50MB)")
    
    app_id = str(uuid.uuid4())
    filename = app_id + "_" + file.filename
    file_path = os.path.join(APP_UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    print(f"[LOG] App uploaded: {request.nome} by {authorization.split(' ')[1][:20]}...")
    
    username = jwt.decode(authorization.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    app_data = create_app(app_id, request.nome, request.categoria, request.descricao, file_path, username)
    apps[app_id] = app_data
    return {"id": app_id, "app": app_data}

@app.post("/apps/rate/{app_id}", dependencies=[Depends(get_current_user)])
async def rate_app(app_id: str, aval: Avaliacao, current_user: str = Depends(get_current_user)):
    if app_id not in apps or apps[app_id]["status"] != "approved":
        raise HTTPException(404, "App not found or not approved")
    app = apps[app_id]
    app["avaliacoes"] += 1
    new_total = app["rating"] * (app["avaliacoes"] - 1) + aval.nota
    app["rating"] = round(new_total / app["avaliacoes"], 1)
    return {"rating": app["rating"]}

@app.post("/apps/comment/{app_id}", dependencies=[Depends(get_current_user)])
async def comment_app(app_id: str, current_user: str = Depends(get_current_user), texto: str = Query(...)):
    if app_id not in apps or apps[app_id]["status"] != "approved":
        raise HTTPException(404, "App not found")
    if len(texto) > 500:
        raise HTTPException(400, "Comentário muito longo")
    apps[app_id]["comments"].append({
        "user": current_user,
        "texto": texto,
        "data": datetime.now().isoformat()
    })
    return {"ok": True}

@app.get("/apps/comments/{app_id}")
async def get_comments(app_id: str):
    if app_id not in apps:
        raise HTTPException(404, "App not found")
    return apps[app_id]["comments"][-20:]  # last 20

@app.get("/apps")
async def get_apps(categoria: Optional[str] = None):
    filtered = {}
    for k, v in apps.items():
        if v["status"] == "approved" and (not categoria or v["categoria"] == categoria):
            v["num_comments"] = len(v["comments"])
            filtered[k] = v
    return filtered

@app.get("/apps/top")
async def get_top_apps(limit: int = 10):
    approved = {k: v for k, v in apps.items() if v["status"] == "approved"}
    scored = sorted(approved.items(), key=lambda x: x[1]["downloads"] + x[1]["rating"] * 10, reverse=True)
    top = dict(scored[:limit])
    for k in top:
        top[k]["num_comments"] = len(top[k]["comments"])
    return top

@app.get("/apps/pending")
async def get_pending_apps(current_user: str = Depends(get_current_user)):
    return {k: v for k, v in apps.items() if v["status"] == "pending"}

@app.post("/apps/approve/{app_id}", dependencies=[Depends(get_current_user)])
async def approve_app(app_id: str, current_user: str = Depends(get_current_user)):
    if app_id not in apps:
        raise HTTPException(404, "App not found")
    apps[app_id]["status"] = "approved"
    return {"status": "approved"}

@app.post("/apps/reject/{app_id}", dependencies=[Depends(get_current_user)])
async def reject_app(app_id: str, current_user: str = Depends(get_current_user)):
    if app_id not in apps:
        raise HTTPException(404, "App not found")
    apps[app_id]["status"] = "rejected"
    return {"status": "rejected"}

@app.get("/apps/download/{app_id}")
async def download_app(app_id: str):
    if app_id not in apps or apps[app_id]["status"] != "approved":
        raise HTTPException(404, "App not available")
    apps[app_id]["downloads"] += 1
    return FileResponse(apps[app_id]["arquivo"])

@app.get("/scripts")
async def get_scripts(categoria: Optional[str] = None, current_user: str = Depends(get_current_user)):
    filtered = {}
    for k, v in scripts.items():
        if v["publico"] or v["owner"] == current_user:
            if categoria is None or v["categoria"] == categoria:
                filtered[k] = v
    return filtered

@app.get("/buscar")
async def buscar(q: str = Query(...), current_user: str = Depends(get_current_user)):
    q_lower = q.lower()
    filtered = {}
    for k, v in scripts.items():
        if (v["publico"] or v["owner"] == current_user) and (
            q_lower in v["nome"].lower() or q_lower in v["descricao"].lower() or q_lower in v["categoria"].lower()
        ):
            filtered[k] = v
    return filtered

@app.post("/executar/{script_id}/{device_id}", dependencies=[Depends(get_current_user)])
async def executar(script_id: str, device_id: str, current_user: str = Depends(get_current_user)):
    if script_id not in scripts or not (scripts[script_id]["publico"] or scripts[script_id]["owner"] == current_user):
        raise HTTPException(403, "Acesso negado")
    scripts[script_id]["execucoes"] += 1
    tarefas.append({
        "id": script_id,
        "device_id": device_id,
        "caminho": scripts[script_id]["path"]
    })
    return {"status": "enviado"}

# ... rest of endpoints with auth where needed
@app.get("/tarefas")
def get_tarefas(device_id: str):
    result = [t for t in tarefas if t["device_id"] == device_id]
    tarefas[:] = [t for t in tarefas if t["device_id"] != device_id]
    return result

@app.get("/download/{filename}")
async def download(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(filepath)

@app.get("/ai/sugestoes/{device_id}")
async def ai_sugestoes(device_id: str):
    status = status_devices.get(device_id, {})
    from backend.services.ai import get_ai_suggestions
    return get_ai_suggestions(status)

@app.get("/ai/busca")
async def ai_busca(q: str, current_user: str = Depends(get_current_user)):
    from backend.services.ai import smart_search
    all_apps = {k: v for k, v in apps.items() if v["status"] == "approved"}
    user_scripts = scripts  # simplify
    return smart_search(q, all_apps, user_scripts)

@app.get("/ai/recomendacoes")
async def ai_recomendacoes(current_user: str = Depends(get_current_user)):
    from backend.services.ai import get_recommendations
    popular = {k: v for k, v in apps.items() if v["status"] == "approved" and v.get("downloads", 0) > 0}
    history = []  # todo
    return get_recommendations(history, popular)

@app.post("/ai/pack-auto")
async def ai_pack_auto(query: str):
    from backend.services.ai import generate_pack
    return {"pack_apps": generate_pack(query), "name": query.capitalize() + " Pack"}

@app.post("/ai/chat")
async def ai_chat(query: str):
    from backend.services.ai import ai_chat
    return ai_chat(query)

@app.post("/resultado")
async def resultado(result: Resultado):
    logs[result.device].append({"timestamp": datetime.now().isoformat(), **result.dict()})
    return {"ok": True}

@app.get("/logs")
async def get_logs(current_user: str = Depends(get_current_user)):
    return logs[current_user][-50:]

@app.post("/favoritar/{script_id}", dependencies=[Depends(get_current_user)])
async def favoritar(script_id: str, current_user: str = Depends(get_current_user)):
    if script_id not in favoritos[current_user]:
        favoritos[current_user].append(script_id)
    return {"ok": True}

@app.get("/favoritos", dependencies=[Depends(get_current_user)])
async def get_favoritos(current_user: str = Depends(get_current_user)):
    return {id: scripts[id] for id in favoritos[current_user] if id in scripts}

@app.post("/avaliar/{script_id}", dependencies=[Depends(get_current_user)])
async def avaliar(script_id: str, aval: Avaliacao, current_user: str = Depends(get_current_user)):
    if script_id not in scripts:
        raise HTTPException(404, "Script não encontrado")
    s = scripts[script_id]
    s["avaliacoes"] += 1
    new_total = s["rating"] * (s["avaliacoes"] - 1) + aval.nota
    s["rating"] = round(new_total / s["avaliacoes"], 1)
    return {"rating": s["rating"]}

@app.post("/register_device")
async def register_device(device: Device):
    devices[device.id] = {"nome": device.nome}
    return {"ok": True}

@app.get("/devices")
def get_devices():
    return devices

@app.post("/status")
async def update_status(status: Status):
    status_devices[status.device] = status.dict()
    # Broadcast WS
    for conn in connection_manager:
        try:
            await conn.send_json({"type": "status", "data": status_devices})
        except:
            connection_manager.discard(conn)
    return {"ok": True}

@app.get("/status")
def get_status():
    return status_devices

@app.post("/regra")
async def create_regra(regra: Regra):
    regras.append(regra.dict())
    return {"ok": True}

@app.get("/regras")
def get_regras():
    return regras

@app.post("/agendar")
async def create_agendamento(ag: Agendamento):
    agendamentos.append({
        "script_id": ag.script_id,
        "device": ag.device,
        "intervalo": ag.intervalo,
        "next_exec": time.time() + ag.intervalo
    })
    return {"ok": True}

@app.get("/agendamentos")
def get_agendamentos():
    return agendamentos

@app.get("/sugestoes/{device_id}")
async def sugestoes(device_id: str):
    status = status_devices.get(device_id, {})
    sugs = []
    if status.get("cpu", 0) > 80:
        sugs.append("CPU alto - sugerir script limpeza")
    if status.get("ram", 0) > 85:
        sugs.append("RAM alta - sugerir otimização")
    return sugs

# WS
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_manager.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.discard(websocket)

# Scheduler
def scheduler_loop():
    while True:
        current_time = time.time()
        for ag in agendamentos[:]:
            if current_time >= ag["next_exec"]:
                tarefas.append({
                    "id": ag["script_id"],
                    "device_id": ag["device"],
                    "caminho": scripts.get(ag["script_id"], {}).get("path", "")
                })
                ag["next_exec"] += ag["intervalo"]
        time.sleep(1)

threading.Thread(target=scheduler_loop, daemon=True).start()

# Auto regras
@app.on_event("startup")
async def startup_event():
    # Auto rule check in status already there
    pass
