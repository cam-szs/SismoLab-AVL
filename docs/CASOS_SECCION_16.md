# Casos mínimos de la sección 16: evidencia

Cada caso usa un archivo reproducible de `samples/`, declara su estado inicial y compara el
resultado esperado con el obtenido. Los resultados "obtenidos" se tomaron ejecutando la
aplicación, y `tests/test_section16_cases.py` los vuelve a verificar en cada ejecución de
`pytest`.

**Estado inicial común**

- Zonas: Valle Central (x 300–500, y 300–500, poblada), Sierra Alta (x 500–700, y 300–500,
  no poblada), Puerto Norte (x 650–900, y 700–950, poblada) y Desierto Sur (x 100–900,
  y 50–250, no poblada).
- Estaciones: ST-1 a ST-5.
- Parámetros: W = 48 h, R = 40 km, L = 3, T = 72 h.
- Modo normal. Los archivos de inserciones y topología fijan el reloj en 2026-10-05 12:00 UTC.

**Cómo se cargan**

- Archivos de inserciones (`caso1`, `caso4`): botón **Cargar inserciones JSON**.
- Archivos de topología (`caso5`, `topologia_*`): botón **Cargar topología JSON**.
- Ráfagas (`caso2`, `caso3`): botón **Cargar ráfaga JSON** del panel de recepción y luego
  **Procesar siguiente reporte** una vez por reporte.

---

## Caso 1. Límites y empates

**Archivo:** `samples/caso1_limites_empates.json` (carga por inserciones).

| Evento | Datos | Prioridad esperada | Obtenida |
|---|---|---|---|
| 401 | M 4,5 · H 30,0 · (500, 400), borde entre zona poblada y no poblada | 3 | 3 (zona poblada: sí) |
| 402 | M 4,5 · H 30,0 · (600, 400), fuera de zona poblada | 2 | 2 |
| 403 | M 4,5 · H 30,1 · (400, 400), en zona poblada | 2 | 2 |
| 404 | M 6,0 · H 300 · (150, 900), fuera de zona | 3 | 3 |
| 406 | M 4,4 · H 10 · (350, 350), en zona poblada | 1 | 1 |
| 405 y 410 | M 4,8 · H 60, mismos P y M | 2 y 2 | 2 y 2 |

**Empate:** 405 y 410 tienen la misma prioridad y magnitud, así que decide el identificador.
Se espera 405 antes que 410 en inorden.

**Obtenido (inorden):** `406, 402, 403, 405, 410, 401, 404`. Las claves son ascendentes y
405 queda antes que 410.

---

## Caso 2. Corrección y reporte antiguo

**Archivo:** `samples/caso2_correccion_reporte_antiguo.json` (ráfaga de 3 reportes del
evento 220).

| Paso | Reporte | Decisión esperada | Obtenido |
|---|---|---|---|
| 1 | ST-1, rev 1: M 4,8 · H 70,0 | alta, prioridad 2 | `created`, P 2 |
| 2 | ST-2, rev 2: M 6,2 · H 15,0 | corrección; la prioridad pasa de 2 a 3 y la clave cambia | `corrected`, P 3, rev 2, estaciones ST-1 y ST-2 |
| 3 | ST-3, rev 1 (antigua) | descartado por antiguo; sin nodo nuevo y sin revertir | `stale`; el evento sigue con M 6,2, H 15,0, rev 2 |

**Obtenido:** el AVL tiene 1 solo nodo. Contadores: 1 corrección aceptada y 1 reporte
descartado. La corrección manual (M 4,8 → 6,2 desde el modal **Corregir**) da el mismo
resultado; la cubre `tests/test_events_queries.py::test_correction_case_from_section_16`.

---

## Caso 3. Reporte tardío

**Archivo:** `samples/caso3_reporte_tardio.json` (ráfaga).

**Política de asociación del equipo:** entre los candidatos (mayor magnitud, ocurrido
estrictamente antes, dentro de W horas y R km), se elige el de mayor magnitud. Si empatan,
el más cercano en tiempo; luego, el más cercano en distancia; y por último, el de menor ID.
La política depende solo de los datos, no del orden de llegada ni de la forma del árbol.

| Momento | Esperado | Obtenido |
|---|---|---|
| Tras procesar 301 (M 5,6, 10:00) y 302 (M 4,2, 10:20) | 302 tiene un candidato, 301, y lo toma como referencia | candidatos `[301]` (0,33 h, 11,66 km), referencia 301 |
| Tras procesar el tardío 303 (M 6,1, ocurrido a las 09:55) | 302 gana el candidato 303 y cambia su referencia por mayor magnitud; 301 también pasa a referirse a 303 | 302: candidatos `[303, 301]`, referencia 303 · 301: referencia 303 · 303: sin candidatos, lo usan 301 y 302 |

Para verlo en la app: abre el evento #302 (clic en el mapa o **Buscar por ID**) antes y
después del tercer paso.

---

## Caso 4. Rotaciones y recuperación

**Parte A, los cuatro casos.** Archivo `samples/caso4_rotaciones.json` (inserciones;
magnitudes 2,8 · 2,7 · 1,2 · 2,4 · 1,5 · 2,1 · 2,9).

| Al insertar | Caso esperado | Obtenido (contadores acumulados) |
|---|---|---|
| 403 | LL (un giro a la derecha) | LL 1 |
| 405 | RL (dos giros) | LL 1, RL 1 |
| 406 | LR (dos giros) | LL 1, RL 1, LR 1 |
| 407 | RR (un giro a la izquierda) | LL 1, RR 1, LR 1, RL 1; giros: 3 a la izquierda y 3 a la derecha |

AVL final: altura 2, raíz 404. Para ver cada caso por separado, se puede insertar en orden
con **Crear evento** y mirar el panel de indicadores después de cada alta.

**Parte B, desbalance mayor que 2 y recuperación.** Archivo `samples/topologia_estres.json`
(topología en modo estrés).

- **Estado cargado:** una cadena de 7 nodos con factores −6, −5, −4, −3, −2, −1 y 0, y altura 6.
- **Auditoría esperada:** orden válido, desbalance esperado y sin errores de metadatos.
  **Obtenido:** igual.
- **Recuperar AVL, esperado:** rotaciones sobre los nodos existentes, el mismo inorden, todos
  los factores en {−1, 0, 1}, auditoría válida y regreso al modo normal.
- **Recuperar AVL, obtenido:** casos RR, RR, RL, RR, RR, RR (5 RR, 1 RL; 6 giros a la
  izquierda y 1 a la derecha), altura 2, el mismo inorden, auditoría válida y modo normal.

---

## Caso 5. Archivo masivo

**Archivo:** `samples/caso5_archivo_masivo.json` (topología). Reloj 2026-10-05 12:00,
T = 72 h.

**Estado inicial:**

```
#504 P1 ─┬─ #502 P1 ─┬─ #501 P1
         │           └─ #503 P1
         └─ #508 P1 ─┬─ #506 P1 ─┬─ #505 P1
                     │           └─ #507 P1
                     └─ #509 P3 ─── #510 P1 (2 h de antigüedad)
```

Los eventos 501–509 tienen unas 100 h de antigüedad.

| Situación | Esperado | Obtenido |
|---|---|---|
| Raíces de prioridad baja con un descendiente de prioridad alta (504 y 508 contienen a 509) | no elegibles | no aparecen entre las elegibles |
| 510 es de prioridad baja pero tiene solo 2 h | no elegible | no aparece |
| Empate de tamaño: 506 y 502 tienen 3 nodos | gana 506, por tener la raíz más profunda (2 frente a 1) | vista previa: raíz 506 con `[505, 506, 507]`, entre 6 ramas elegibles |
| Tercer criterio (mismo tamaño y profundidad) | 507 antes que 505, por mayor ID | en las alternativas, 507 aparece antes que 505 |
| Ejecutar | 3 eventos pasan al histórico | 7 activos y 3 históricos; archivos masivos 1, eventos archivados 3 |
| Deshacer una vez | vuelve la rama completa | 10 activos y 0 históricos |
| Sin ramas elegibles (cambiar T a 200) | se informa y no cambia nada | "no hay ramas elegibles" |

---

## Caso 6. Persistencia y consistencia

| Prueba | Archivo o acción | Esperado | Obtenido |
|---|---|---|---|
| Topología normal | `topologia_normal.json` | el mismo árbol, la cola `[180]` y los mismos contadores | igual |
| Topología en estrés | `topologia_estres.json` | se carga en modo estrés con el mismo árbol desbalanceado | igual |
| Archivo inconsistente | `topologia_invalida.json` (altura de la raíz alterada) | se rechaza y el estado actual no cambia | error "altura almacenada incorrecta en el evento #110"; el estado sigue intacto |
| Versión después de reiniciar | **Guardar versión**, reiniciar el backend y **Restaurar** | se recupera el escenario guardado y la restauración se puede deshacer | igual (`data/versions/` persiste en disco) |
| Deshacer una corrección | corregir un evento y luego **Deshacer** | vuelven la clave, la revisión y los contadores anteriores | igual (`test_undo_and_versions_restore_counters_and_bst_topology`) |
| Deshacer un paso de cola | procesar un reporte y luego **Deshacer** | el reporte vuelve a su posición en la cola | igual (`test_queue_step_shows_rotations_and_undo_restores_queue_position`) |

---

## Otros archivos de prueba

- `insercion_aleatoria.json` e `insercion_ascendente.json`: comparación AVL vs BST con
  distintos órdenes. Con el orden ascendente, el BST queda con altura 11 y el AVL con altura 3.
- `rafaga_reportes.json`: ráfaga de 4 estaciones con altas, una confirmación, una
  confirmación repetida, una corrección que cambia la clave, un reporte antiguo y un conflicto.
