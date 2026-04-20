print("Servidor iniciando...")
import os
os.makedirs("uploads", exist_ok=True)
from backend.main import app

@app.get("/test")
def test():
    return {"msg": "API funcionando"}

