# SismoLab AVL: architecture and 12-day plan

## Decision

The project will use a Python backend and a React frontend.

- `domain/` owns the AVL, BST, entities, queue, undo stack, and invariants.
- `services/` coordinates event lifecycle, reports, associations, archive, metrics, and persistence.
- `api/` is a thin HTTP adapter. It validates requests, calls services, and returns JSON. It must not contain AVL or business rules.
- `frontend/` contains React components and presentation state. It must not duplicate domain rules.
- `tests/` verifies domain and service behavior. API tests only verify the adapter contract.

React was selected because the team already wants to work with it. The cost is accepted and bounded by keeping one Python process for the backend and one simple Vite development process for the frontend. No WebSocket is planned; the UI refreshes after each user action.

## Request flow

```text
React component -> fetch(api endpoint) -> api/app.py -> service -> domain structure
                                      <- JSON response <-
```

The API will expose resource-oriented endpoints gradually. The first slice is `GET /api/health` and `GET /api/state`; event mutation endpoints are added only after the corresponding service is implemented and tested.

## Responsibilities

### Students

- **Jeronimo:** AVL and BST implementation, rotations, deletion, recovery, and structural audit tests.
- **Camilo:** event/report lifecycle, FIFO processing, validation, associations, and service tests.
- **Team member 3:** React views, API integration, JSON persistence/version screens, and presentation tests.
- **All three:** understand every merged change, review each other's code, prepare the mandatory cases, and practice manual modifications for the defense.

The assignments are a starting point, not isolated ownership. Each feature is merged only after another teammate can explain its invariants and modify it without AI assistance.

## Twelve-day sequence

1. Agree on data contracts, key comparison, snapshot format, and branch strategy.
2. Implement and test BST/AVL insertion and rotations.
3. Implement AVL deletion and audit helpers.
4. Implement event validation, priority, identity lookup, and lifecycle operations.
5. Implement reports, revisions, conflicts, and FIFO processing.
6. Implement associations, including a deterministic `refresh_all` policy for late reports.
7. Implement archive, stress mode, global recovery, and metrics.
8. Implement persistence, topology validation, undo, and versions.
9. Connect API endpoints to completed services.
10. Build React tree, event form, queue, and result panels.
11. Add map, audit, history/version views, and mandatory scenario data.
12. Run tests, repair defects, rehearse the defense, and freeze the submitted version.

## API rules

- JSON uses numeric event identifiers and decimal values with a dot.
- Errors return a stable object such as `{ "error": "..." }`.
- The backend is the only source of truth for priority, key, associations, metrics, and structure.
- The frontend may format values but may not recalculate business decisions.
