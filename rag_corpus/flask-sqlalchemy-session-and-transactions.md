# db.session: adding, committing and deleting

Flask-SQLAlchemy tracks pending changes in `db.session`, a per-request scoped session
object. Nothing is written to the database until `db.session.commit()` is called.

```python
new_task = Todo(content="buy milk", priority=2)
db.session.add(new_task)      # stage the new object
db.session.commit()           # flush + write the transaction to disk

task = Todo.query.get_or_404(id)
db.session.delete(task)
db.session.commit()

task.content = "new content"  # mutating an already-tracked object
db.session.commit()           # SQLAlchemy detects the change automatically
```

If `commit()` raises an exception (e.g. a constraint violation, or — as in the schema-drift
case described in `flask-sqlalchemy-migrations-vs-create-all.md` — a missing column). The
session should be rolled back with `db.session.rollback()` before continuing to use it in
the same request; otherwise, the session is left in a broken state and subsequent queries
in that request can raise unrelated errors. A common pattern:

```python
try:
    db.session.add(new_task)
    db.session.commit()
except Exception:
    db.session.rollback()
    return 'There was an issue adding your task', 500
```

Existing code that catches a bare `except:` without rolling back the session (a common
shortcut in small tutorial projects) can leave the session in a bad state for the rest of
the request lifecycle — worth flagging as a fragility if touched during a change.
