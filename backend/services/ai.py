from typing import Dict, List
import os
import uuid

def get_ai_suggestions(status_data):
    suggestions = []
    if status_data.get('cpu', 0) > 80:
        suggestions.append({
            "title": "CPU Alto - Otimizar",
            "action": "exec_script",
            "id": "cpu_optimizer",
            "description": "Fecha apps desnecessários e otimiza processos"
        })
    if status_data.get('ram', 0) > 85:
        suggestions.append({
            "title": "RAM Cheia - Limpeza",
            "action": "exec_script",
            "id": "ram_cleaner",
            "description": "Limpa cache e fecha memória vazia"
        })
    if status_data.get('disk', 0) > 90:
        suggestions.append({
            "title": "Disco Cheio - Cleanup",
            "action": "exec_script",
            "id": "disk_cleanup",
            "description": "Remove temps e arquivos grandes"
        })
    return suggestions

def smart_search(query, apps, scripts):
    q_lower = query.lower()
    results = []
    # Keyword matching
    for app_id, app in apps.items():
        if any(word in app.get('nome', '').lower() or word in app.get('descricao', '').lower() or word in app.get('categoria', '').lower() for word in q_lower.split()):
            results.append({"type": "app", "id": app_id, "score": 1.0, "match": app.get('nome', '')})
    for script_id, script in scripts.items():
        if any(word in script.get('nome', '').lower() or word in script.get('descricao', '').lower() for word in q_lower.split()):
            results.append({"type": "script", "id": script_id, "score": 1.0, "match": script.get('nome', '')})
    return sorted(results, key=lambda x: x['score'], reverse=True)[:10]

def get_recommendations(user_history, popular_apps):
    recs = []
    # Simple: popular + user liked cat
    for app_id, app in popular_apps.items():
        recs.append({"id": app_id, "reason": "popular"})
    return recs[:5]

def generate_pack(query):
    packs = {
        "setup gamer": ["fps_booster", "gamer_clean", "low_latency"],
        "limpar pc": ["ram_cleaner", "disk_cleanup", "temp_remove"],
        "otimizar": ["cpu_optimizer", "startup_disable"]
    }
    return packs.get(query.lower(), [])

def ai_chat(query):
    intent_map = {
        "limp": "ram_cleaner",
        "cpu": "cpu_optimizer",
        "fps": "fps_booster",
        "gamer": "setup gamer pack"
    }
    for key, action in intent_map.items():
        if key in query.lower():
            return {"intent": action, "response": f"Sugestão: {action}", "action": "suggest"}
    return {"response": "Não entendi. Tente 'limpar pc' ou 'melhorar fps'"}
