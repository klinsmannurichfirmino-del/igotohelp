print("Servidor iniciando...")
import os
os.makedirs("uploads", exist_ok=True)

from backend.main import app

@app.get("/")
async def root():
    return {"status": "online"}

@app.get("/test")
def test():
    return {"msg": "API funcionando"}

@app.get("/debug")
def debug():
    return {
        "apps_json_existe": os.path.exists("apps.json"),
        "uploads_existe": os.path.exists("uploads"),
        "sandbox_existe": os.path.exists("sandbox")
    }

