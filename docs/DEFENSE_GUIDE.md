# SismoLab AVL: guía de defensa

## Ejecución

Backend:

```powershell
.\venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Pruebas:

```powershell
.\venv\Scripts\python.exe -m pytest -q
cd frontend
npm test
npm run build
```

## Orden recomendado para la demostración

1. Abrir el frontend y mostrar el estado `normal`, la cola y las métricas.
2. Crear varios reportes, encolarlos y procesarlos uno por uno para demostrar FIFO.
3. Mostrar la clave `(P, M, I)` y los árboles AVL/BST.
4. Cambiar a `stress`, insertar una secuencia ascendente y mostrar el desbalance temporal.
5. Ejecutar `Recuperar AVL` y verificar que el árbol vuelve a estar balanceado.
6. Corregir un evento para mostrar el cambio de prioridad, revisión y reordenamiento.
7. Archivar un evento, recuperarlo y revisar el historial.
8. Avanzar el reloj simulado y ejecutar el archivado de rama.
9. Descargar JSON, modificar una copia válida y cargarla desde el frontend.
10. Intentar cargar un JSON corrupto y mostrar que el estado anterior no cambia.
11. Guardar una versión, reiniciar el backend, actualizar la lista y restaurarla.
12. Ejecutar la auditoría y explicar errores de metadatos, nodos desbalanceados y modo estrés.

## Requisitos demostrados

| Requisito | Evidencia |
|---|---|
| BST/AVL, inserción y orden | `tests/test_avl_tree.py` |
| LL, RR, LR y RL | `tests/test_avl_tree.py` y `docs/DEMO_CASES.md` |
| FIFO y revisiones | `tests/test_skeleton.py` |
| Stress y recuperación rotacional | `tests/test_skeleton.py` |
| Reloj simulado y archivo | `tests/test_defense_cases.py` |
| JSON atómico y corrupción | `tests/test_defense_cases.py` |
| Versiones persistentes | `tests/test_defense_cases.py` |
| API y frontend | `tests/test_skeleton.py` y `frontend/src/App.test.jsx` |

## Explicación breve de la arquitectura

- `domain/`: invariantes, entidades, AVL, BST, cola, pila y escenario.
- `services/`: ciclo de vida de eventos, asociaciones, archivo y métricas.
- `api/`: adaptación HTTP, serialización y persistencia.
- `frontend/`: presentación, controles y estado de la interfaz.

El backend es la fuente de verdad para prioridades, claves, asociaciones,
métricas, historial y topología.
