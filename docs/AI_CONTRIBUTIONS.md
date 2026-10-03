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

## Current implementation alignment

- **Date:** 2026-10-03
- **Scope:** execution modes, AVL recovery, archival, undo, persistence, queries, and React controls.
- **Files:** `domain/scenario.py`, `domain/avl.py`, `services/report_processor.py`, `services/association_service.py`, `services/persistence_service.py`, `api/app.py`, `frontend/src/App.jsx`, `frontend/src/styles.css`, `README.md`, `docs/ARCHITECTURE.md`.
- **Request:** align the implementation with the project PDF, where normal/stress are the execution modes and W/R/L/T are parameters.
- **Result:** separated execution mode from parameters, added rotational recovery, branch archival selection, complete-state undo snapshots, persistent named versions, topology validation/rehydration, academic query endpoints, and frontend controls.
- **Human review required:** the team must verify the rotation proof, branch tie-breaks, snapshot semantics, and the mandatory demonstration cases before submission.
- **Owner for understanding:** all three teammates.

## Final attribution statement

This project was primarily developed by the student team. The AI assistant supported the process through architecture advice, debugging, and targeted corrections, but the main implementation, understanding, and responsibility for the final project outcomes remain with the students. The final version should therefore be defended and explained by the student team as their own work, with the AI contributions recorded as support rather than as the primary source of the project logic.
- **Request:** clarify the real project rule for duplicate event IDs, remove the misleading default `event=None` insertion path, and clean up the breadth-first alias so the API naming does not hide a duplicate method.
- **Result:** `DuplicateKeyError` is documented as an internal structural guard, not as the business-level validation for duplicate identifiers; `insert()` now requires a real event payload; and the tree exposes a single canonical breadth-first traversal name.
- **Human review required:** confirm that id uniqueness checks belong in the service-layer index before any AVL/BST insert, and that the tree remains a structural primitive rather than the place where business validation happens.
- **Owner for understanding:** all three teammates; the team must explain to the group that `id` uniqueness is enforced before calling `tree.insert()` even when the key changes due to priority or magnitude updates.

## AVL implementation adaptation

- **Date:** 2026-10-03
- **Scope:** `domain/avl.py`.
- **Request:** adapt the supplied AVL implementation to the project's `BSTree`, `Node`, and `EventKey` contracts.
- **Result:** added AVL insertion/deletion rebalancing through subtree-returning rotations, rotation metrics, stress mode, traversal aliases, and tree export helpers.
- **Human review required:** verify rotation invariants, deletion behavior, and the exported JSON shape before merging.
- **Owner for understanding:** all three teammates.

## Review-state synchronization and repository cleanup

- **Date:** 2026-10-03
- **Scope:** `domain/bst.py`, `services/event_service.py`, `tests/test_event_service_core.py`, `.gitignore`, `requirements.txt`.
- **Request:** correct the inconsistency where marking an event as reviewed updated the service index but left the AVL node with the previous immutable event snapshot, and complete the first repository stabilization phase.
- **Result:** added a structural value-update operation, synchronized the AVL value during `mark_reviewed`, added regression coverage, declared the API test client dependency, and stopped tracking generated Python cache files while ignoring the local virtual environment.
- **Human review required:** verify the immutable-event replacement semantics, the cleanup diff, and the full test result before committing.
- **Owner for understanding:** all three teammates.

## Domain and service integration

- **Date:** 2026-10-03
- **Scope:** `domain/avl.py`, `domain/scenario.py`, `services/report_processor.py`, `services/persistence_service.py`, `api/app.py`, and regression tests.
- **Request:** connect scenario stress mode to report processing, provide global AVL recovery, expose structural metrics, and validate JSON reconstruction.
- **Result:** `ReportProcessor` now owns a synchronized AVL for active events, scenario mode `T` enables deferred balancing, recovery restores the global AVL invariant, API state exposes AVL and processing metrics, and persistence supports explicit merge loading.
- **Human review required:** verify the stress-burst policy, recovery transition, serialized state compatibility, and AVL metrics before merging.
- **Owner for understanding:** all three teammates.

## API and frontend integration

- **Date:** 2026-10-03
- **Scope:** `api/app.py`, `services/report_processor.py`, `frontend/src/App.jsx`, `frontend/src/styles.css`, and `tests/test_skeleton.py`.
- **Request:** complete the API/frontend phase with endpoint verification, stress and recovery controls, event correction/deletion, AVL visualization, structural metrics, loading states, and error feedback.
- **Result:** added explicit event mutation endpoints, exposed the exported AVL structure and metrics, added React controls for stress/recovery/correction/deletion, and covered the new API flows with regression tests.
- **Human review required:** verify the HTTP contract, destructive-action confirmation, UI state transitions, and the displayed AVL topology before merging.
- **Owner for understanding:** all three teammates.

## Stress mode implementation

- **Date:** 2026-10-03
- **Scope:** `domain/avl.py`, `tests/test_avl_tree.py`.
- **Request:** implement deferred AVL balancing during report bursts and global recovery.
- **Result:** added stress-mode toggles, height maintenance without rotations, balanced-tree recovery, invariant auditing, balance checks, rotation metrics, and stress deletion coverage.
- **Human review required:** verify the burst policy, recovery timing, and metrics against the project scenario before merging.
- **Owner for understanding:** all three teammates.
