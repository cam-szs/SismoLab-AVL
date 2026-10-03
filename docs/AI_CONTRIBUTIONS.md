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

The core implementation of this project was carried out by the student team. The students owned the design, coding, debugging, and defense preparation of the functional requirements, especially the structural and domain logic that defines the project behavior.

The following areas were primarily developed by the students:

- AVL/BST structure, insertion rules, rotations, ordering logic, and the corresponding structural invariants.
- Event lifecycle design, report validation, priority and key semantics, and event revision handling.
- Report queue processing, event state transitions, archive/recover workflow, and metric generation.
- Association logic, persistence flow, state snapshot export/import, and rehydration consistency checks.
- API contract wiring between the Python backend and the React frontend.
- Regression tests covering the project requirements, edge cases, and behavior validation before submission.

The student team is therefore the primary owner of the functional implementation and should be able to explain and modify these pieces without assistance.

## AI-assisted support and targeted corrections

The AI assistant provided support in selected areas, mainly as a technical reviewer, debugger, and corrective partner. The AI did not replace the project ownership of the student team; it helped clarify architecture, find root causes, and refine implementation details once the main logic had already been defined by the students.

Examples of AI-assisted work recorded here:

- **Date:** 2026-10-03
- **Scope:** architecture review, API-state debugging, and project stabilization.
- **Files:** `api/app.py`, `tests/test_skeleton.py`, `frontend/src/App.jsx`, `docs/AI_CONTRIBUTIONS.md`.
- **Request:** diagnose why scenario state and backend status were inconsistent, confirm the correct flow between live memory state and persisted snapshots, and align the API with the expected behavior.
- **Result:** the issue was traced to stale snapshot rehydration overwriting the current in-memory scenario state; the live state endpoint was corrected to reflect the active runtime state, while explicit load operations remained responsible for snapshot restoration.
- **Human review required:** the student team reviewed the root cause, validated the fix, and confirmed the behavior through the project tests.
- **Owner for understanding:** the student team, with AI support for debugging and refinement.

- **Date:** 2026-10-03
- **Scope:** BST contract cleanup and duplicate-key clarification.
- **Files:** `domain/bst.py`, `docs/AI_CONTRIBUTIONS.md`.
- **Request:** clarify the difference between structural BST invariants and business-level uniqueness validation, and reduce ambiguity in the public API.
- **Result:** the documentation and method contract were corrected so the tree remains a structural primitive, while uniqueness checks are treated as a service-layer concern rather than an internal tree rule.
- **Human review required:** the student team reviewed the rule and agreed with the boundary between business validation and tree structure.
- **Owner for understanding:** the student team; the AI only assisted with clarifying wording and implementation boundaries.

- **Date:** 2026-10-03
- **Scope:** association test repair and deterministic validation.
- **Files:** `tests/test_skeleton.py`, `services/association_service.py`, `api/app.py`.
- **Request:** fix the regression case to reflect the actual matching rule and verify the association API behavior.
- **Result:** the test data was aligned with the established project rule for source/reference timing and magnitude relationships, and the API endpoint was checked for correct output and counts.
- **Human review required:** the student team confirmed that the test reflects the original domain requirement rather than a synthetic shortcut.
- **Owner for understanding:** the student team, with AI assistance in reproducing and validating the failing scenario.

## Final attribution statement

This project was primarily developed by the student team. The AI assistant supported the process through architecture advice, debugging, and targeted corrections, but the main implementation, understanding, and responsibility for the final project outcomes remain with the students. The final version should therefore be defended and explained by the student team as their own work, with the AI contributions recorded as support rather than as the primary source of the project logic.
