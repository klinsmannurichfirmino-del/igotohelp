print("Servidor iniciando...")
import os
os.makedirs("uploads", exist_ok=True)
from backend.main import app

@app.get("/")
async def root():
    return {"status": "online"}

