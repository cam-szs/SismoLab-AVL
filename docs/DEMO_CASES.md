# Demonstration cases

These cases map the minimum demonstrations from section 16 of the project
specification to the current application.

## 1. Limits and ties

Create events with magnitudes `4.5` and `6.0`, depth `30.0`, and an epicenter
on a populated-zone border. Verify inclusive priority rules. Insert equal
priority/magnitude events with different identifiers and verify identifier
ordering in the AVL key `(P, M, I)`.

## 2. Correction and stale report

Create an event with `M=4.8`, `H=70.0`, then correct it to `M=6.2`,
`H=15.0`. Its priority must change from 2 to 3, its revision must increase,
and its status must become pending. Submit a lower revision afterwards; the
report must be rejected as stale without changing the event.

## 3. Late report and associations

Create a magnitude `5.6` event at 10:00 and a magnitude `4.2` event at 10:20.
Submit a magnitude `6.1` event at 09:55 within the configured `W` and `R`
limits. Verify the deterministic reference policy and that active and archived
events are considered while deleted events are excluded.

## 4. Rotations and stress recovery

Run LL, RR, LR, and RL insertion sequences in normal mode. Then switch to
`stress`, enqueue an ascending burst, and verify that ordering remains valid
while balance may fail. Invoke global recovery and verify that recovery uses
rotations, preserves event identities, restores all factors to `-1..1`, and
returns to `normal`.

## 5. Mass archival

Advance the simulation clock beyond `T`, create a low-priority eligible
subtree, and call `POST /api/archive/branch`. Verify the largest eligible
branch, the depth and identifier tie-breaks, the fixed affected set, and one
single undo action for the whole archive.

## 6. Persistence and versions

Save a normal snapshot and a stressed snapshot. Load both through the
topology loader and verify active nodes, heights, factors, queue order,
history, parameters, mode, and metrics. Corrupt a key, height, factor, link,
or duplicate identity and verify that loading fails without changing the
current state. Save a named version, restart, restore it, and undo the
restoration.

## Relevant endpoints

- `POST /api/scenario/mode` with `normal` or `stress`
- `POST /api/scenario/parameters` with `W`, `R`, `L`, and `T`
- `POST /api/scenario/recover`
- `POST /api/archive/branch`
- `POST /api/undo`
- `POST /api/versions/{name}`
- `POST /api/versions/{name}/restore`
- `GET /api/audit`
- `GET /api/queries/top-pending?limit=5`
- `GET /api/queries/expensive`
