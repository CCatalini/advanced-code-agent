# Evidencia de tareas ejecutadas

Transcripciones completas (JSON) en
[`logs/runs/advanced-coding-agent/`](../logs/runs/advanced-coding-agent/). Este documento
resume las corridas reales y qué se observa en cada una.

> **Nota sobre alcance**: la corrida completa del caso de uso (`scripts/run_feature_task.py`)
> se cortó dos veces por falta de crédito de la cuenta de Anthropic. En el segundo intento
> (ver Tarea 4), Explorer, Researcher, Implementer y Tester ya habían terminado su trabajo
> — el crédito se agotó justo cuando el agente principal iba a delegar en el Reviewer. El
> texto final de Tester no quedó grabado en ningún log (el proceso murió antes de guardar el
> `TaskState`), así que la evidencia de esa tarea se reconstruyó inspeccionando los archivos
> reales que quedaron en `flask-class` y corriendo `pytest` de forma independiente — no es el
> subagente "diciendo que pasa", es una verificación externa de que efectivamente pasa.
> Una vez renovado el crédito, se corrió `scripts/run_reviewer_only.py` (Tarea 4) y
> `scripts/run_memory_test.py` (Tarea 5) para cerrar ambos tests — ver más abajo.

---

## Tarea 1 — Explorer entendiendo `flask-class` (Explorer + RAG scope)

**Pedido** (parte del pedido completo del caso de uso, delegado por el agente principal):
entender la estructura de `flask-class` antes de decidir cómo agregar prioridad/fecha de
vencimiento y filtro.

**Qué hizo el subagente**: 7 iteraciones de tool calls (`list_files`/`read_file`, sin
`write_file` — Explorer no tiene esa tool disponible). Exploró la raíz, `templates/`,
`static/`, `data/`, `instance/`, y leyó `app.py`, `init_db.py`, `requirements.txt` y los 4
templates HTML.

**Fuentes usadas**: `[REPO]` únicamente — es exactamente lo esperado de Explorer (no tiene
acceso a `rag_search`/`web_search`).

**Extracto real del resultado**:
> *"No test files exist anywhere in the repo (no `tests/` dir, no `test_*.py`, no pytest
> config)."* ... *"`app.py` (full contents)"* [transcribe el archivo completo, incluyendo
> el modelo `Todo` con `id`, `content`, `completed`, `date_created`] ... *"unpinned —
> actual installed versions from `.venv`: Flask 3.1.3, SQLAlchemy 2.0.51,
> Flask-SQLAlchemy 3.1.1..."*

**Qué se observa**: Explorer identificó correctamente la ausencia total de tests (dato
crítico para lo que después tiene que hacer el Tester) y las versiones reales instaladas —
no asumidas del `requirements.txt` (que no tiene versiones fijadas), sino leídas del
`.venv` real. Texto completo en
`logs/runs/advanced-coding-agent/2026-07-18T16-17-15.097784+00-00.json` →
`subagent_results.Explorer[0].result`.

---

## Tarea 2 — Researcher resolviendo el problema de schema drift (RAG + fallback a web)

**Pedido**: investigar cómo agregar las columnas `priority`/`due_date` a un modelo
Flask-SQLAlchemy cuya base SQLite ya existe, sin Flask-Migrate instalado, más el patrón de
filtro/orden y de testing.

**Qué hizo el subagente**: 3 iteraciones. Llamó `rag_search` cuatro veces con distintas
queries (schema drift, tipos de columna, queries con filtro/orden, testing con pytest), y
recién después llamó `web_search` **una vez**, para un dato puntual que el corpus no cubre.

**Fuentes usadas y cómo se diferenciaron** (texto real, tal cual lo devolvió el modelo):

> *"`db.create_all()` only creates tables that don't yet exist — it never diffs/alters an
> existing table, so simply adding columns to the model will not touch the on-disk
> `instance/database.db` **[RAG: flask-sqlalchemy-migrations-vs-create-all.md]**."*
>
> *"Important SQLite constraint confirmed via web search: you cannot add a `NOT NULL`
> column without also supplying a `DEFAULT` value... **[WEB:
> https://sqlite.org/forum/info/ffa52447275d247a]**."*
>
> *"Use SQLAlchemy 2.0's `text()` + `conn.execute(...)` — both are equivalent since this is
> a single DDL statement outside the ORM **[INFERENCE, based on SQLAlchemy 2.0 execution
> model]**."*

**Qué se observa**: los 3 tipos de etiqueta que pide la consigna (RAG/WEB/INFERENCE)
aparecen efectivamente diferenciados en la misma respuesta, no mezclados en prosa
indistinguible. El Researcher también propuso un script concreto
(`migrate_add_columns.py`, con `ALTER TABLE ... ADD COLUMN`) para resolver el schema drift
sin perder datos — la clase de recomendación que justifica tener un RAG especializado en
vez de dejar que el modelo improvise de memoria general. Texto completo en el mismo archivo
de log → `subagent_results.Researcher[0].result`.

---

## Tarea 3 — Detección de loops (determinística, sin costo de API)

**Cómo se ejecutó**: [`scripts/run_loop_guard_test.py`](../scripts/run_loop_guard_test.py),
llamando a `execute_tool()` directamente 5 veces con el mismo comando que falla siempre
igual (`python -c "import nonexistent_module_xyz"`).

**Resultado real**:
```
call 1: STDOUT: ...                                    (ejecución normal)
call 2: [REPEATED ACTION] ...                            (aviso suave)
call 3: [LOOP DETECTED] ...                                (aviso fuerte)
call 4: [HARD_STOP] Automatic loop guard triggered ...       (corte duro)
call 5: [HARD_STOP] Automatic loop guard triggered ...       (se mantiene cortando)
```

**Qué se observa**: la escalada es automática y no depende de que el modelo "decida"
obedecer — a partir de la 4ª repetición idéntica, `execute_tool()` deja de ejecutar la tool
de nuevo. Esto es exactamente el requisito de *"detectar cuándo está repitiendo acciones
sin avanzar... cambiar de estrategia, replanificar, detenerse"* de la consigna, verificado
de forma determinística (no depende de la variabilidad del modelo en una corrida particular).

---

## Tarea 4 — Implementer + Tester end-to-end sobre `flask-class` (el caso de uso real)

**Pedido**: el pedido completo de la sección 7 del plan — agregar `priority`/`due_date` al
modelo `Todo`, filtro/orden por query params, y tests, usando los 5 subagentes.

**Qué hizo el Implementer** (verificado leyendo el diff real, `git diff --stat` en
`flask-class`: `app.py` +133/-2, `init_db.py` +3/-1, `requirements.txt` +1,
`templates/index.html` +38/-1, `templates/update.html` +17/-2):
- Agregó las columnas `priority` (`Integer, nullable=False, default=0`) y `due_date`
  (`DateTime, nullable=True`) al modelo `Todo`.
- **Resolvió el problema de schema drift que Researcher había anticipado** (Tarea 2): en
  vez de solo confiar en `db.create_all()`, escribió una función `run_migrations()` que
  inspecciona las columnas reales de la tabla (`sqlalchemy.inspect`) y agrega con
  `ALTER TABLE ... ADD COLUMN` únicamente las que faltan — idempotente, no rompe si se
  corre dos veces ni si la tabla es nueva.
- Extendió la ruta `/` para leer `priority`, `completed` y `sort_by`/`order` de
  `request.args` y armar la query con `.filter(...)`/`.order_by(...)` condicionalmente,
  cayendo al comportamiento anterior si no se pasa ningún filtro (no rompe los links
  existentes).
- Agregó parsing defensivo (`_parse_priority`, `_parse_due_date`) que ignora valores
  inválidos en vez de tirar un 500.

**Qué hizo el Tester** (verificado leyendo los archivos que quedaron en
`flask-class/tests/`, ninguno existía antes de esta corrida):
`conftest.py`, `test_index_get.py`, `test_index_post.py`, `test_update.py`,
`test_delete.py`, `test_filters_and_sorting.py`. El `conftest.py` resuelve un problema
real y no trivial de Flask-SQLAlchemy: como `app.py` crea el engine apuntado a la DB de
producción (`sqlite:///database.db`) al importarse, simplemente cambiar
`app.config['SQLALCHEMY_DATABASE_URI']` después no alcanza — hay que borrar
`app.extensions['sqlalchemy']` y volver a llamar `db.init_app(app)` para que reconstruya
el engine contra una DB en memoria. El comentario que dejó el propio Tester en el archivo
documenta este gotcha con detalle.

**Verificación independiente** (corrida por fuera del agente, sin gastar API, para no
depender del crédito):
```
$ cd flask-class && source .venv/bin/activate && pytest -q
...
18 passed, 23 warnings in 0.07s
```

**Qué se observa**: el Implementer no solo agregó las columnas — aplicó exactamente la
recomendación que el Researcher había traído del RAG en la Tarea 2 (migración manual en
vez de confiar en `create_all()`), lo que muestra que el resumen del Researcher realmente
viajó y se usó, no fue un adorno. El Tester, al no tener suite previa, no se limitó a un
test superficial: escribió 18 casos cubriendo altas/filtros/orden/update/delete, y resolvió
un problema de aislamiento de base de datos que ni el pedido original ni el Researcher
habían anticipado.

**Veredicto del Reviewer** (corrido con `scripts/run_reviewer_only.py` una vez renovado el
crédito, sin repetir Explorer/Researcher/Implementer/Tester — leyó el diff real y los 6
archivos de test ya en disco):

> *"1. Does it satisfy the request? ... matches spec. 2. Does it avoid breaking existing
> functionality? ... Full suite: 18/18 passing... 3. Scope ... appropriately scoped, not
> excessive."*
> **Verdict: APPROVED**

El Reviewer también identificó por su cuenta (sin que se le pidiera) que el Implementer
había resuelto el schema drift con un `run_migrations()` idempotente en vez de borrar la
base — la misma decisión que había anticipado el Researcher en la Tarea 2 — y marcó dos
observaciones menores no bloqueantes (filtro de prioridad es exact-match, no rango; un
detalle cosmético en el `<select>` del template ante un `sort_by` inválido).

**Qué se observa**: el Test 4 queda cerrado end-to-end con los 5 subagentes reales
(Explorer → Researcher → Implementer → Tester → Reviewer), cada uno con su resultado
verificable de forma independiente (archivos en disco, `pytest` en verde, veredicto
explícito) — no hay ningún paso "simulado".

---

## Tarea 5 — Memoria persistente entre sesiones (Test 2)

**Cómo se ejecutó**: [`scripts/run_memory_test.py`](../scripts/run_memory_test.py). Carga
`memory/project_memory.json` (ya con la entrada de la Tarea 4) y le hace una pregunta al
agente principal **sin pasarle nada del historial de la sesión anterior** — solo lo que
`build_system_prompt` inyecta vía `memory.compact_summary()`.

**Pregunta**: *"¿qué cambios se hicieron en este proyecto y por qué hubo que recrear la
base de datos en vez de solo agregar una columna?"*

**Resultado real**: el agente respondió citando explícitamente que su fuente es la memoria
persistente ("Basándome únicamente en lo que quedó registrado de la sesión anterior..."),
reconstruyó correctamente el razonamiento de `create_all()` vs. columnas nuevas, y —lo más
importante— **fue honesto sobre el límite de lo que sabía**: como esa corrida puntual de
memoria se disparó contra una entrada vieja (de un intento anterior que solo había llegado
a Explorer/Researcher), el agente aclaró textualmente que no tenía guardados "los hallazgos
concretos... así que lo anterior es la explicación más plausible dado el contexto, pero no
puedo confirmarte con certeza". **Subagentes usados en esta sesión: ninguno** — respondió
enteramente desde memoria, sin re-explorar el repo.

**Qué se observa**: esto demuestra dos cosas a la vez — que la memoria compacta sí se usa
en vez de ignorarse, y que el agente no inventa certeza que no tiene cuando la memoria es
parcial (justo el comportamiento de "reconocer cuándo no hay evidencia suficiente" que pide
la consigna). Después de esta corrida se actualizó manualmente la entrada de memoria para
reflejar el estado final real (los 5 subagentes, archivos modificados, veredicto del
Reviewer), documentado en `IMPLEMENTATION_LOG.md`.

**Segunda corrida, con la memoria ya corregida** (una vez arreglado Langfuse): el agente
volvió a responder solo desde memoria, pero esta vez con un matiz distinto al anterior —
en vez de reconocer el límite, **afirmó con seguridad que "la única vía práctica fue
borrar la base y recrearla"**. Eso es plausible pero **no es lo que pasó**: el Implementer
resolvió el schema drift con un `run_migrations()` que hace `ALTER TABLE` in-place, sin
perder datos (Tarea 4). El motivo es que `memory.record_from_task()` guarda *qué* archivos
se tocaron y *qué* subagentes intervinieron, pero no *cómo* se resolvió el problema técnico
puntual — el agente completó ese hueco con una inferencia general y bien argumentada, pero
incorrecta en el detalle. Es un hallazgo real y útil para la Reflexión: la memoria compacta
es económica en tokens, pero al no guardar decisiones técnicas específicas, el modelo puede
rellenar el vacío con una suposición razonable que no siempre coincide con lo que realmente
se hizo.

---