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

## AVL vs BST visualization and comparison mirror

- **Date:** 2026-10-03
- **Scope:** `domain/bst.py`, `domain/avl.py`, `services/report_processor.py`, `api/app.py`, `frontend/src/App.jsx`, `frontend/src/styles.css`, `tests/test_skeleton.py`, `docs/AI_CONTRIBUTIONS.md`.
- **Request:** render the structure with circular nodes joined by straight edges and expose a parallel BST so the AVL and the BST can be compared visually.
- **Result:** the topology exporter moved to `BSTree` (shared by the AVL through inheritance); `ReportProcessor` now keeps an unrotated `BSTree` mirror fed with the same insertions, corrections, deletions, and archival as the AVL; `/api/state`, the metrics payload, `persist`, and `load` expose the `bst` topology plus size/height/leaf metrics; the React view replaces the nested list with an SVG `TreeView` (circles, straight lines, priority colors, balance-factor badges) and shows AVL and BST side by side; added regression tests for the mirror and the API contract.
- **Human review required:** confirm the mirror stays synchronized under corrections, archival, and deletion, and verify the SVG layout and responsive breakpoints.
- **Owner for understanding:** all three teammates.

## Zones, manual creation, lookup by id and section 11 queries

- **Date:** 2026-10-05
- **Scope:** `domain/scenario.py`, `services/report_processor.py`, `api/app.py`, `frontend/src/App.jsx`, `frontend/src/hooks/useScenarioState.js`, `frontend/src/components/NodeDetails.jsx`, `frontend/src/components/TerritoryMap.jsx`, `frontend/src/api.js`, `frontend/src/styles.css`, `tests/test_events_queries.py`.
- **Request:** compare the implementation against the assignment and close the mandatory gaps in sections 3, 6 and 11.
- **Result:** default fictional zones (with a shared border to show the "populated wins" rule) that are saved, restored and checked against each event's stored `populated_zone`; `POST /api/events` for manual creation with full validation and no partial state; `GET /api/events/{id}` returning active/archived/deleted status, node depth, visited nodes, height, balance, expensive-access flag and associations; manual corrections recompute the populated zone and may change the occurrence time; queries for top-k pending, magnitude interval (prunes subtrees using the key bounds), depth and date interval, and expensive access, all reporting examined AVL nodes; rejected actions no longer push an undo step; the React app gained a territory map, create/lookup and query panels, and the previously unused correction dialog.
- **Human review required:** verify the zone geometry, the pruning argument in `_magnitude_span`, the cost analysis of each query, and the new UI flows.
- **Owner for understanding:** Jeronimo (queries and pruning), all three teammates (creation and lookup).

## Restorable counters, AVL cases, recovery cost, archive preview, audit and comparison

- **Date:** 2026-10-05
- **Scope:** `domain/avl.py`, `domain/bst.py`, `domain/scenario.py`, `services/report_processor.py`, `services/comparison_service.py`, `api/app.py`, `frontend/src/App.jsx`, `frontend/src/hooks/useScenarioState.js`, `frontend/src/styles.css`, `tests/test_avl_tree.py`, `tests/test_events_queries.py`, `tests/test_counters_recovery.py`.
- **Request:** close the gaps in sections 8, 10, 12, 13 and 14 (restorable state and indicators).
- **Result:** the AVL counts LL/RR/LR/RL cases separately from elementary rotations and logs every case; global recovery repairs subtrees bottom-up with an explicit termination argument and reports its cost; counters, stations and the BST topology are saved and restored by undo, versions and export; queue steps report their rotations and the UI offers continuous processing with a pause; branch archival has a preview with the justification and alternatives; the audit lists one issue per inconsistent event (order against all ancestors, uniqueness, references, heights, balance) and separates expected stress imbalance; loads support both insertion and topology modes; a comparison endpoint builds AVL and BST for given/ascending/descending/random orders and reports height, leaves and search comparisons; the UI shows indicators and the four traversals.
- **Human review required:** verify the recovery termination argument, the audit checks, the counters schema in the exported JSON and the comparison metrics.
- **Owner for understanding:** Jeronimo (AVL cases, recovery, audit, comparison), all three teammates (counters and UI).

## Spec compliance fixes: fixed paths, action log, expensive mark, stations

- **Date:** 2026-10-05
- **Scope:** `api/app.py`, `frontend/src/App.jsx`, `frontend/src/hooks/useScenarioState.js`, `frontend/src/components/TreeView.jsx`, `frontend/src/components/NodeDetails.jsx`, `frontend/src/components/EventList.jsx`, `frontend/src/styles.css`, `tests/test_counters_recovery.py`, `tests/test_skeleton.py`, `tests/test_defense_cases.py`.
- **Request:** fix the remaining rules the implementation did not meet.
- **Result:** removed the fixed `data/scenario_state.json` path (export downloads the live state; server load/persist require a user-chosen path); append-only action log with the counters each action changed, shown in the UI; the AVL view marks expensive access with a ring separate from the priority colour and states when stress mode breaks the AVL condition; reports, manual creations and loaded files must use a station of the fixed scenario network (old API tests now use valid station codes); the UI no longer archives single events or reactivates archived ones by hand (only branch archival and newer revisions do); mode, parameter, clock and load actions push an undo step only when they succeed; leaving stress mode logs the recovery cost.
- **Human review required:** confirm the decision to hide single-event archive/recover (the `/api/archive` and `/api/recover` endpoints remain for tests) and the action-log semantics.
- **Owner for understanding:** all three teammates.

## Report bursts loaded from a file

- **Date:** 2026-10-06
- **Scope:** `api/app.py`, `frontend/src/App.jsx`, `frontend/src/hooks/useScenarioState.js`, `frontend/src/components/QueueItem.jsx`, `frontend/src/styles.css`, `tests/test_counters_recovery.py`, `samples/rafaga_reportes.json`.
- **Request:** let the user queue a burst of reports from N stations with a file chooser (section 8).
- **Result:** `POST /api/queue/load` validates every report (ranges, station network, occurrence time) before queuing any, keeps file order, and counts as one undoable action in the action log; the queue panel has a "Cargar ráfaga JSON" button and shows revision and position; a sample burst covers new events, confirmations, a key-changing correction, a stale report and a conflict.
- **Human review required:** check the burst JSON schema and the all-or-nothing validation.
- **Owner for understanding:** all three teammates.

## Visible action feedback and Spanish error messages

- **Date:** 2026-10-06
- **Scope:** `frontend/src/hooks/useScenarioState.js`, `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/src/errorMessages.js`, `frontend/src/errorMessages.test.js`, `frontend/src/styles.css`, `frontend/index.html`.
- **Request:** a rejected action (e.g. creating a duplicate id) showed no message; translate backend errors to Spanish.
- **Result:** the 3-second state polling no longer clears action errors (connection errors use their own state); action results appear as fixed toasts that stay until dismissed; backend messages are translated in one place before display, keeping the English API contract and its tests unchanged; added a favicon.
- **Human review required:** check the wording of the translated messages.
- **Owner for understanding:** all three teammates.

## Deletion with the in-order predecessor; typed clock hours

- **Date:** 2026-10-06
- **Scope:** `domain/bst.py`, `tests/test_avl_tree.py`, `frontend/src/components/ClockControls.jsx`, `frontend/src/App.jsx`, `frontend/src/App.test.jsx`, `frontend/src/styles.css`.
- **Request:** when a node with two children is deleted, replace it with its in-order predecessor; advance the clock with a typed number of hours instead of fixed buttons.
- **Result:** `BSTree._delete` (shared by the AVL) detaches the largest node of the left subtree with `_detach_max`, rebalancing that path, and relinks it in place of the deleted node instead of copying key and event, so every node keeps its own event; tests cover the root case, a deep predecessor, a deletion that triggers a rotation, the plain BST and random deletions. The clock panel shows the current simulation time and an hours field.
- **Human review required:** trace one two-children deletion by hand, including the rebalancing of the predecessor's path.
- **Owner for understanding:** Jeronimo.
