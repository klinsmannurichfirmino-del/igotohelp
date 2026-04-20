# iGoToHelp SaaS TODO

1. [ ] requirements.txt +pyjwt
2. [ ] backend/main.py: JWT auth, public/private scripts w/ owner, file type limit, per-user logs/favs, /sugestoes/{device}
3. [ ] agent/agent.py: auto register device, timeout/retry
4. [ ] frontend/index.html: JWT auth header, public filter, devices/store sections, sugestoes

**Test:** pip install -r requirements.txt && python -m uvicorn backend.main:app --reload && python agent/agent.py && open frontend/index.html
