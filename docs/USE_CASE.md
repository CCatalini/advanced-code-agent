# Caso de uso

## Repositorio/proyecto utilizado

[`sencina/flask-class`](https://github.com/sencina/flask-class): una aplicación TODO
construida con Flask + Flask-SQLAlchemy (material de tutorial/curso), clonada como carpeta
hermana de este repo (`.../artificial-intelligence/flask-class`). El agente apunta a ella a
través del campo `workspace: ../flask-class` de [`agent.config.yaml`](../agent.config.yaml).

Se eligió un repo real pero acotado (`app.py` de ~86 líneas, un modelo
`Todo`, 4 rutas) en vez de un repo externo grande y desconocido: da tiempo para ejercitar
los 5 subagentes sobre un cambio genuino sin el costo de indexar y aprender un codebase
grande. El repo **no** tiene tests ni herramienta de migraciones —
eso no se ocultó, se convirtió en parte de lo que el caso de uso tiene que resolver (ver
`docs/IMPLEMENTATION_LOG.md`, Paso 0).

## Objetivo concreto

Agregarle al modelo `Todo` dos campos nuevos:
- `priority` (entero, default 0)
- `due_date` (fecha opcional)

Y una forma de **filtrar y ordenar** la lista de tareas por prioridad y estado
(completada/pendiente), vía query params en la ruta `/` (ej. `/?priority=2&sort=due_date`).

Esto es "agregar una funcionalidad a un proyecto existente" (uno de los dos casos de uso de
ejemplo de la consigna), con la particularidad extra de que la base de datos real ya existe
(creada una vez con `init_db.py`) y no hay Flask-Migrate/Alembic instalado — el agente tiene
que descubrir y resolver ese problema de schema drift, no solo escribir el código Python.

## Criterio de éxito

La tarea se considera cumplida cuando:
1. El modelo `Todo` tiene las columnas `priority` y `due_date`.
2. La base de datos real (`instance/database.db`) refleja esas columnas sin perder las
   filas existentes (o, si se optó por recrearla, eso queda explícito y justificado).
3. La ruta `/` acepta `priority` y `sort` como query params opcionales, sin romper el
   comportamiento actual cuando no se pasan.
4. Existe una suite de tests (`pytest`, con `app.test_client()`) que corre en verde,
   cubriendo el filtro/orden nuevo y una verificación de que las rutas existentes
   (`/`, `/delete/<id>`, `/update/<id>`) siguen funcionando.
5. El Reviewer certificó (`APPROVED`) que el diff responde al pedido sin cambios fuera de
   alcance.

## Estado final

Los 5 criterios de éxito se cumplieron con los 5 subagentes corriendo contra la API real
(ver `docs/EVIDENCE.md`, Tareas 1, 2 y 4): `priority`/`due_date` agregadas sin perder datos
(vía un helper `run_migrations()` idempotente que el propio Implementer decidió escribir),
filtro/orden funcionando por query params, 18/18 tests de pytest en verde, y **veredicto
del Reviewer: APPROVED**.
