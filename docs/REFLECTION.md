# Reflexión

## Qué funcionó bien

- El patrón "subagente = función con su propio loop de `messages.create`" resultó 
  simple de implementar y de explicar, sin necesitar ningún framework de
  orquestación. Extender de 1 subagente (Explorer) a 5 fue casi mecánico una vez que el
  `orchestrator.py` y el registro por rol (`SUBAGENT_REGISTRY`) quedaron armados.
- El RAG con corpus propio + `sentence-transformers` + numpy funcionó mejor de lo esperado:
  con solo 31 chunks, la query de prueba sobre schema drift trajo como top-3 exactamente
  los documentos relevantes (scores 0.73/0.72/0.69), y el Researcher citó las fuentes
  correctamente sin que hiciera falta iterar el prompt.
- La detección de loops determinística (tool calls) se pudo verificar sin gastar un solo
  token de la API 

## Qué falló (y qué se corrigió)

- Bug real encontrado en la corrida completa del caso de uso: cuando `stop_reason ==
  "max_tokens"`, el loop principal trataba la respuesta truncada (y vacía) como la
  respuesta final del agente. Se corrigió agregando un chequeo explícito de ese
  `stop_reason` en `main_agent.py` y `orchestrator.py`, más subir `max_tokens` de 1024 a
  4096 en ambos loops. Esto solo apareció al correr una tarea real con contexto grande
  (resultados largos de Explorer + Researcher acumulados) — no se hubiera detectado con
  pruebas triviales de una sola tool call.
- La cuenta de Anthropic se quedó sin crédito a mitad de la corrida completa del caso de
  uso (Test 4), **dos veces**. No es una falla de diseño del sistema — es un límite
  operativo externo — pero sí cambió el plan: se documentó todo lo verificable sin costo
  (el detector de loops es 100% determinístico) y se dejaron scripts listos (`scripts/`)
  para terminar en cuanto haya crédito disponible. En el segundo intento, Explorer,
  Researcher, Implementer y Tester ya habían terminado antes de que se cortara — el
  Implementer resolvió correctamente el schema drift que Researcher había anticipado
  (migración manual vía `ALTER TABLE`, no solo `create_all()`), y el Tester escribió 18
  tests que pasan (verificado corriendo `pytest` de forma independiente, ver
  `docs/EVIDENCE.md` Tarea 4) — solo faltó el veredicto del Reviewer. Se dejó
  `scripts/run_reviewer_only.py` para no tener que rehacer los 4 subagentes anteriores
  una vez que haya crédito de nuevo.
- Bug real de infraestructura, no de diseño: en la primera corrida completa, el Tester
  intentó `pip install pytest` dentro del venv propio del repo target (`flask-class/.venv`,
  que no lo tenía instalado), y esa acción cae bajo `commands.require_approval` en
  `agent.config.yaml`. Como la corrida era en background (sin terminal interactiva), el
  `input()` de `execution.py` quedó esperando una aprobación que nunca iba a llegar, y el
  modelo gastó varias iteraciones probando variantes del mismo comando en vez de detectar
  que estaba bloqueado. Se corrigió en dos frentes: (1) se pre-instalaron las dependencias
  del target en su propio venv para que el Tester no necesite pedir `pip install` en
  primer lugar, y (2) se agregó una salvaguarda real en `execution.py`
  (`sys.stdin.isatty()`) que auto-rechaza inmediatamente cuando no hay una terminal
  interactiva conectada, en vez de bloquear el proceso. Es un caso concreto de "requiere
  aprobación" pensado para un humano presente que no contempla corridas automatizadas —
  vale la pena mencionarlo en la presentación como una limitación real que encontramos y
  corregimos, no solo como diseño teórico.
- Al quedarme con poco crédito de la API (< USD 0.50), armé [`agent/tests/`](../agent/tests/), 
  una suite de 43 tests con `pytest` que ejercita
  `policy.py`, `state.py`, `memory.py`, `context.py`, `execution.py` y
  `rag/retrieve.py` **sin llamar nunca a la API de Anthropic** (el retrieval del RAG usa
  el modelo de embeddings local; las llamadas a `messages.create` de `context._summarize`
  se reemplazan por un stub en los tests). Escribir estos tests encontró un bug real:
  `memory.load_memory()` devolvía una copia superficial de `DEFAULT_MEMORY`, así que
  mutar el resultado (`memory["decisions"].append(...)`, algo que `record_from_task` hace
  siempre) contaminaba el diccionario global entre llamadas dentro del mismo proceso — se
  corrigió con `copy.deepcopy`. No se hubiera detectado sin escribir los tests, porque en
  una sesión interactiva normal `load_memory()` solo se llama una vez por proceso.
- La memoria persistente guarda *qué* archivos se tocaron y *qué* subagentes intervinieron,
  pero no *cómo* se resolvió un problema técnico puntual. En una corrida real de Test 2, el
  agente afirmó que la base de datos se había recreado desde cero
  — cuando en realidad el Implementer la había resuelto con un `run_migrations()`
  que altera la tabla sin perder datos. No es un error de diseño grave,
  pero sí un límite real de guardar memoria a nivel de "qué pasó" en vez de "cómo se
  resolvió" — ver `docs/EVIDENCE.md`, Tarea 5.

## Cuándo se detectaron loops o falta de evidencia 

- El detector de loops se disparó tal como estaba diseñado en la prueba dedicada
  (`scripts/run_loop_guard_test.py`): escalada de aviso suave → aviso fuerte → corte duro
  ante la misma tool call repetida.
- La "falta de evidencia" más real no fue del agente sobre el código, sino
  nuestra sobre la API (el corte de crédito) — que terminó siendo, sin planearlo, un
  ejemplo genuino de "reconocer cuándo no se tiene lo necesario para continuar y decirlo
  explícitamente" en vez de simular que todo salió bien.

## Qué mejoraría con más tiempo

- **Loop detection semántico**: hoy la huella es exacta (mismo tool, mismos args, mismo
  resultado). Un agente que reformula ligeramente el mismo comando fallido en cada intento
  (en vez de repetirlo textual) no dispararía el detector — una versión con embeddings
  sobre los resultados sería más robusta.
- **Prompt caching** de Anthropic sobre el system prompt largo y los chunks de RAG, para
  reducir costo/latencia en conversaciones largas
- **Políticas por rol de subagente** en el propio `agent.config.yaml` (hoy los permisos por
  rol están hardcodeados en `SUBAGENT_REGISTRY`, no son data-driven)
- **Eficiencia del Tester**: en la corrida real se lo vio re-verificar de más — corriendo
  `pytest` varias veces con leves variaciones, chequeando el checksum (`md5`) del archivo
  de la base de datos entre corridas, releyendo archivos ya leídos — en vez de confiar en
  un resultado limpio de una sola corrida. No es un loop (cada comando era distinto, así
  que el detector de la sección de manejo de contexto no lo frenaba, correctamente: no era
  un loop, era over-verification) pero sí gastó iteraciones y tokens de más. Con más
  tiempo, ajustaría el system prompt del Tester para que se conforme con una corrida
  limpia de `pytest` salvo que el resultado sea ambiguo.
- **Reranking o un corpus más grande para el RAG**: con 31 chunks el retrieval ya funciona
  bien, pero no probamos el sistema bajo un corpus con cientos de documentos, donde
  probablemente haría falta Chroma/FAISS y quizás un reranker.