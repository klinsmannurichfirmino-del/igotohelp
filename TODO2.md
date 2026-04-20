# iGoToHelp Avançado TODO

**Plan Breakdown:**
1. [ ] Update backend/main.py (multi-device, WS, status, regras, agendamento thread)
2. [ ] Update requirements.txt (+psutil)
3. [ ] Update agent/agent.py (DEVICE_ID, status psutil 2s, logs/, error detect)
4. [ ] Update frontend/index.html (dropdown device, WS status, regras/agenda hacker style)

**Followup:**
1. pip install -r requirements.txt
2. python -m uvicorn backend.main:app --reload
3. python agent/agent.py (set DEVICE_ID)
4. frontend/index.html
