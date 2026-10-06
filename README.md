# SismoLab AVL

Observatorio sísmico simulado para el proyecto de Estructuras de Datos. El catálogo de
eventos activos es un **árbol AVL** ordenado por la clave **K = (prioridad, magnitud,
identificador)**. Junto a él hay un **BST** de comparación, una **cola FIFO** de reportes, una
**pila** para deshacer, un modo **estrés** con balanceo diferido y recuperación global, y
persistencia en JSON.

- **Backend:** Python + FastAPI (`domain/`, `services/`, `api/`). Es la fuente de verdad:
  calcula prioridades, claves, asociaciones, métricas y topología.
- **Frontend:** React + Vite (`frontend/`). Solo presenta y envía acciones.

El territorio y las reglas son ficticios y académicos; no constituyen una evaluación real del
riesgo sísmico.

## Requisitos

- Python 3.11 o superior (probado con 3.13)
- Node.js 20 o superior (probado con 20.19) y npm

## Instalación (una sola vez)

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend && npm install && cd ..
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend; npm install; cd ..
```

## Ejecución

Se necesitan dos terminales, ambas en la carpeta del proyecto.

**Terminal 1, backend (API en http://127.0.0.1:8000)**

```bash
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
uvicorn api.app:app --reload --port 8000
```

**Terminal 2, frontend (http://localhost:5173)**

```bash
cd frontend
npm run dev
```

Abre http://localhost:5173 en el navegador. La interfaz indica arriba a la derecha si está
conectada al backend.

## Pruebas

```bash
python -m pytest -q                # backend (con el entorno virtual activo)
cd frontend && npm test            # frontend
cd frontend && npm run build       # verifica que el frontend compile
```

## Archivos de prueba (`samples/`)

| Archivo | Cómo se carga | Qué demuestra |
|---|---|---|
| `caso1_limites_empates.json` | Cargar inserciones JSON | límites de prioridad, borde de zona y desempate por ID |
| `caso2_correccion_reporte_antiguo.json` | Cargar ráfaga JSON | corrección que cambia la clave y reporte antiguo descartado |
| `caso3_reporte_tardio.json` | Cargar ráfaga JSON | reporte tardío y política de asociación |
| `caso4_rotaciones.json` | Cargar inserciones JSON | los casos LL, RR, LR y RL |
| `caso5_archivo_masivo.json` | Cargar topología JSON | rama elegible, desempates y raíz bloqueada por un descendiente de prioridad alta |
| `topologia_normal.json` | Cargar topología JSON | restaurar un escenario completo en modo normal |
| `topologia_estres.json` | Cargar topología JSON | árbol desbalanceado (factor −6) y recuperación global |
| `topologia_invalida.json` | Cargar topología JSON | archivo inconsistente que se rechaza sin cambiar el estado |
| `insercion_aleatoria.json`, `insercion_ascendente.json` | Cargar inserciones JSON | comparación AVL vs BST según el orden de inserción |
| `rafaga_reportes.json` | Cargar ráfaga JSON | ráfaga de 4 estaciones con todas las decisiones posibles |

El estado inicial, los pasos y los resultados esperados y obtenidos de cada caso de la §16
están en [docs/CASOS_SECCION_16.md](docs/CASOS_SECCION_16.md).

## Modos y parámetros

- **Modo normal:** inserciones, correcciones, eliminaciones y archivos terminan con un AVL
  válido.
- **Modo estrés:** se conserva el orden BST pero se aplazan las rotaciones hasta la
  recuperación global (botón *Recuperar AVL*). El regreso al modo normal solo se completa si
  la auditoría confirma el equilibrio.

Parámetros del escenario, que se pueden cambiar desde la interfaz:

| Parámetro | Significado | Inicial |
|---|---|---|
| `W` | ventana de tiempo para asociar eventos | 48 h |
| `R` | distancia máxima para asociar eventos | 40 km |
| `L` | profundidad de nodo a partir de la cual el acceso es costoso | 3 |
| `T` | antigüedad mínima para archivar una rama | 72 h |

El reloj de simulación es explícito, se guarda con el escenario y solo avanza por acción del
usuario.

## Estructura del repositorio

```
domain/      AVL, BST, nodo, clave K, evento, reporte, cola FIFO, pila, escenario
services/    procesamiento de reportes, asociaciones, comparación AVL/BST, persistencia
api/         adaptador HTTP (FastAPI): validación, serialización, deshacer y versiones
frontend/    interfaz React (árboles, mapa, cola, consultas, auditoría, historial)
samples/     archivos JSON de prueba
tests/       pruebas del backend (pytest)
docs/        arquitectura, casos de la §16, guía de defensa y registro de uso de IA
```

## Documentación

- [docs/CASOS_SECCION_16.md](docs/CASOS_SECCION_16.md): evidencia de los casos mínimos
- [docs/DEFENSE_GUIDE.md](docs/DEFENSE_GUIDE.md): guía para la demostración y la defensa
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): decisiones de arquitectura
- [docs/AI_CONTRIBUTIONS.md](docs/AI_CONTRIBUTIONS.md): registro del uso de IA

Las versiones guardadas se escriben en `data/versions/`, que no se sube al repositorio.
