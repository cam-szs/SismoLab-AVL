# SismoLab AVL

This repository contains the SismoLab AVL academic project. The application is
being migrated to a React frontend with a Python API while the domain remains
in Python.

## Current setup

The React scaffold is in `frontend/` and the FastAPI adapter is in `api/`.
The AVL, BST, report processor, persistence, API, and React controls are
implemented as explicit student-owned components. See `docs/ARCHITECTURE.md`
for the twelve-day plan and `docs/AI_CONTRIBUTIONS.md`
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
```

The Vite development server uses `http://localhost:5173` and the API uses
`http://127.0.0.1:8000` by default.

## Execution modes and parameters

The application has two execution modes:

- `normal`: insertions, corrections, deletions, and archival finish with a
  valid AVL.
- `stress`: mutations preserve BST ordering but defer rotations until global
  recovery.

`W`, `R`, `L`, and `T` are scenario parameters, not modes:

- `W`: association time window, initially 48 hours.
- `R`: association distance, initially 40 km.
- `L`: expensive-access depth limit, initially 3.
- `T`: minimum branch age for archival, initially 72 hours.

The API exposes these controls through `/api/scenario/parameters`, global
recovery through `/api/scenario/recover`, and undo through `/api/undo`.
