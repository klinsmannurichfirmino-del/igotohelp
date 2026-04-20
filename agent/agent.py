import requests
import time
import subprocess
import os
import psutil
from urllib.parse import urlparse

DEVICE_ID = "pc-casa"  # Change this for each device

SCRIPTS_DIR = "scripts"
LOGS_DIR = "logs"
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

print(f"Agente {DEVICE_ID} iniciado.")

executados = set()

def send_status():
    try:
        status = {
            "cpu": psutil.cpu_percent(interval=1),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,  # /
            "device": DEVICE_ID
        }
        requests.post(f"{BACKEND_URL}/status", json=status)
    except Exception as e:
        print(f"Status error: {e}")

while True:
    try:
        # Send status
        send_status()
        
        # Get tasks
        resp = requests.get(f"{BACKEND_URL}/tarefas?device_id={DEVICE_ID}")
        tarefas = resp.json()
        
        for tarefa in tarefas:
            task_id = tarefa["id"]
            if task_id in executados:
                continue
            executados.add(task_id)
            
            if tarefa.get("type") == "app":
                print(f"[APP] {task_id} on {DEVICE_ID}")
                download_url = f"{BACKEND_URL}/apps/download/{task_id}"
                filename = f"app_{task_id}.exe"  # default ext
            else:
                print(f"[SCRIPT] {task_id} on {DEVICE_ID}")
                caminho = tarefa["caminho"]
                filename = os.path.basename(caminho)
                download_url = f"{BACKEND_URL}/download/{filename}"
            
            # Download
            file_resp = requests.get(download_url)
            file_resp.raise_for_status()
            
            local_path = os.path.join(SCRIPTS_DIR, filename)
            with open(local_path, "wb") as f:
                f.write(file_resp.content)
            
            print(f"Executando {filename} ({tarefa.get('type', 'script')})")
            
            # Execute
            result = subprocess.run([local_path], shell=True, capture_output=True, text=True, cwd=SCRIPTS_DIR, timeout=60)
            
            # Local log
            log_filename = f"{filename}_{int(time.time())}.log"
            with open(os.path.join(LOGS_DIR, log_filename), "w") as f:
                f.write(f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}\nRETCODE: {result.returncode}\n")
            
            # Result back
            requests.post(f"{BACKEND_URL}/resultado", json={
                "script": filename,
                "saida": result.stdout[:1000],  # limit
                "erro": result.stderr[:1000],
                "device": DEVICE_ID,
                "retcode": result.returncode,
                "type": tarefa.get('type', 'script')
            })
            print(f"Done {filename} rc={result.returncode}")
            
    except subprocess.TimeoutExpired:
        print(f"Timeout {filename}")
        requests.post(f"{BACKEND_URL}/resultado", json={
            "script": filename,
            "saida": "",
            "erro": "timeout",
            "device": DEVICE_ID,
            "retcode": 999
        })
    except Exception as e:
        print(f"Erro loop: {e}")
    
    time.sleep(2)

