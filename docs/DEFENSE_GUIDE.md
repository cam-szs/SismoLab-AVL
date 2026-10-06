# SismoLab AVL: guía de defensa

## Ejecución

Las instrucciones completas para macOS, Linux y Windows están en el `README.md`. En resumen,
desde la carpeta del proyecto y con el entorno virtual `.venv` activo:

```bash
uvicorn api.app:app --reload --port 8000     # terminal 1: backend
cd frontend && npm run dev                   # terminal 2: frontend en http://localhost:5173
python -m pytest -q                          # pruebas del backend
cd frontend && npm test                      # pruebas del frontend
```

En Windows, el entorno se activa con `.\.venv\Scripts\Activate.ps1`.

## Orden recomendado para la demostración

Los archivos están en `samples/`. El detalle de cada caso, con resultados esperados y
obtenidos, está en `docs/CASOS_SECCION_16.md`.

1. Mostrar el modo normal, el mapa con las zonas y estaciones, la cola vacía y los indicadores.
2. **Límites y empates:** cargar `caso1_limites_empates.json` (inserciones) y abrir los
   eventos 401, 402 y 403 para mostrar sus prioridades; señalar en el inorden que 405 va antes
   que 410.
3. **Crear y consultar:** crear un evento a mano, intentar repetir su ID (se rechaza) y
   buscarlo por ID para mostrar la profundidad, la altura, el factor de balance y las
   asociaciones.
4. **Cola FIFO:** cargar `caso2_correccion_reporte_antiguo.json` (ráfaga) y procesar paso a
   paso: alta, corrección que cambia la clave y reporte antiguo descartado. Deshacer un paso
   para mostrar que el reporte vuelve a la cola.
5. **Reporte tardío:** cargar `caso3_reporte_tardio.json` y mostrar cómo cambia la referencia
   del evento 302.
6. **Rotaciones:** cargar `caso4_rotaciones.json` (inserciones) y mostrar los contadores LL,
   RR, LR y RL.
7. **Estrés y recuperación:** cargar `topologia_estres.json`, auditar (desbalance esperado),
   presionar *Recuperar AVL* y mostrar el costo de la recuperación y el regreso a normal.
8. **Archivo masivo:** cargar `caso5_archivo_masivo.json`, ver la vista previa (raíces 504 y
   508 bloqueadas por 509, desempate 506 frente a 502), ejecutar y deshacer. Cambiar T a 200
   para el caso sin ramas elegibles.
9. **Consultas y desempeño:** ejecutar las consultas (nodos examinados) y la comparación AVL
   vs BST; con `insercion_ascendente.json` el BST degenera.
10. **Persistencia:** exportar el JSON, cargar `topologia_invalida.json` (se rechaza sin cambiar
    el estado), guardar una versión, reiniciar el backend y restaurarla; luego deshacer.
11. **Historial y auditoría:** mostrar el historial de acciones con los contadores de cada
    acción y la auditoría por evento.

## Requisitos demostrados

| Requisito | Evidencia |
|---|---|
| Casos mínimos de la §16 | `docs/CASOS_SECCION_16.md` y `tests/test_section16_cases.py` |
| BST/AVL, inserción, eliminación con predecesor y orden | `tests/test_avl_tree.py` |
| LL, RR, LR, RL y recuperación con diferencias mayores que 2 | `tests/test_counters_recovery.py` |
| Creación, consulta por ID, corrección y consultas de la §11 | `tests/test_events_queries.py` |
| FIFO, revisiones, ráfagas y conflictos | `tests/test_skeleton.py` y `tests/test_counters_recovery.py` |
| Reloj simulado y archivo masivo | `tests/test_defense_cases.py` y `tests/test_counters_recovery.py` |
| JSON atómico, cargas por inserción y topología, archivos de ejemplo | `tests/test_samples.py` y `tests/test_defense_cases.py` |
| Deshacer, contadores restaurables y versiones persistentes | `tests/test_counters_recovery.py` |
| API y frontend | `tests/test_skeleton.py` y `frontend/src/App.test.jsx` |

## Explicación breve de la arquitectura

- `domain/`: invariantes, entidades, AVL, BST, cola, pila y escenario.
- `services/`: ciclo de vida de eventos, asociaciones, archivo y métricas.
- `api/`: adaptación HTTP, serialización y persistencia.
- `frontend/`: presentación, controles y estado de la interfaz.

El backend es la fuente de verdad para prioridades, claves, asociaciones,
métricas, historial y topología.
