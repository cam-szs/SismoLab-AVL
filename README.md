# SismoLab AVL

This repository contains the SismoLab AVL academic project. The application is
being migrated to a React frontend with a Python API while the domain remains
in Python.

## Current setup

The React scaffold is in `frontend/` and the FastAPI adapter is in `api/`.
The AVL, BST, and business services are still explicit student-owned stubs.
See `docs/ARCHITECTURE.md` for the twelve-day plan and `docs/AI_CONTRIBUTIONS.md`
for the required record of AI assistance.

### Backend

```powershell
python -m pip install -r requirements.txt
uvicorn api.app:app --reload
```

### Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server uses `http://localhost:5173` and the API uses
`http://127.0.0.1:8000` by default.
