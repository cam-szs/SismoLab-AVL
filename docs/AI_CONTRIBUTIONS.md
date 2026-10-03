# AI contributions

This file records assistance received from AI during the project. The team must update it after every assisted change and review the linked code manually.

## Rules for recording assistance

For each contribution, record the date, files, request, result, human review, and the teammate who can explain and modify it. AI-generated code is not accepted into the final branch until two teammates understand it and the relevant tests pass.

## Initial contribution

- **Date:** 2026-09-24
- **Scope:** project architecture and web integration scaffold.
- **Files:** `docs/ARCHITECTURE.md`, `docs/AI_CONTRIBUTIONS.md`, `api/app.py`, `frontend/package.json`, `frontend/index.html`, `frontend/src/main.jsx`, `frontend/src/App.jsx`, `frontend/src/styles.css`, `requirements.txt`.
- **Request:** define a feasible React architecture for the existing Python skeleton and create the smallest runnable frontend/backend boundary.
- **Human review required:** confirm the request flow, endpoint naming, ownership split, and all starter code before extending it.
- **Owner for understanding:** all three teammates.

## Student-owned work

The students must implement the AVL/BST algorithms, event rules, report state machine, associations, archive/recovery, persistence validation, undo/version behavior, and the mandatory test cases. AI may explain or review these areas, but the implementation and defense preparation should be done by the students and recorded here whenever assistance is used.

## Additional contribution

- **Date:** 2026-10-03
- **Scope:** BST contract cleanup and scope clarification for duplicate-key handling.
- **Files:** `domain/bst.py`, `docs/AI_CONTRIBUTIONS.md`.
- **Request:** clarify the real project rule for duplicate event IDs, remove the misleading default `event=None` insertion path, and clean up the breadth-first alias so the API naming does not hide a duplicate method.
- **Result:** `DuplicateKeyError` is documented as an internal structural guard, not as the business-level validation for duplicate identifiers; `insert()` now requires a real event payload; and the tree exposes a single canonical breadth-first traversal name.
- **Human review required:** confirm that id uniqueness checks belong in the service-layer index before any AVL/BST insert, and that the tree remains a structural primitive rather than the place where business validation happens.
- **Owner for understanding:** all three teammates; the team must explain to the group that `id` uniqueness is enforced before calling `tree.insert()` even when the key changes due to priority or magnitude updates.
