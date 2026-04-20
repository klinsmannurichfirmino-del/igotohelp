# iGoToHelp Moderno TODO

**Info Gathered:**
- Current: root main.py (basic backend), agent/agent.py, frontend/index.html.
- Target: backend/main.py, agent/agent.py, frontend/index.html (enhanced), uploads/.
- New: rich upload, search, fav/rating/user/auth, agent dedupe, CORS, modern UI.

**Plan:**
1. [x] Create backend/main.py with full enhanced FastAPI (groups, CORS, models, all endpoints).
2. [x] Create root run.py for `python -m uvicorn backend.main:app --reload`.
3. [x] Update agent/agent.py with executados set dedupe.
4. [x] Replace frontend/index.html with modern dark app-store style (login, upload fields, search/filter, cards, sidebar).
5. [x] Cleanup old backend/ dir if empty.

**Ready!** Run: python -m uvicorn backend.main:app --reload

**Dependent Files:**
- New: backend/main.py, run.py
- Edit: agent/agent.py, frontend/index.html

**Followup steps:**
1. pip install -r requirements.txt (add pydantic if needed).
2. python -m uvicorn backend.main:app --reload
3. python agent/agent.py
4. Open frontend/index.html

Approve?
