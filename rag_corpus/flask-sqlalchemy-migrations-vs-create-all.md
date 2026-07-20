# db.create_all() vs. migrations (Alembic/Flask-Migrate)

`db.create_all()` inspects the models currently defined and issues `CREATE TABLE IF NOT
EXISTS` statements for any table that does not yet exist in the target database. It does
**not** diff existing tables against the current model definitions, and it will not add,
remove, or alter columns on a table that is already present — it silently does nothing for
that table.

This means that in a project which only calls `db.create_all()` once (typically from a
one-off `init_db.py` script) and has no migrations tool installed, adding a new column to a
model (e.g. `priority = db.Column(db.Integer, default=0)` on an existing `Todo` model) will
**not** appear in the real SQLite file on disk. Any query that references the new column
(directly or through the ORM) will fail at runtime with an error such as:

```
sqlite3.OperationalError: no such column: todo.priority
```

This is a schema-drift problem, not a bug in the query itself — the Python class and the
actual table have diverged. There are two common ways to resolve it for a small project
without migration tooling:

1. **Recreate the database.** Delete the existing SQLite file (or the `instance/`
   folder it lives in) and re-run the init script (e.g. `python init_db.py`) so
   `create_all()` creates the table fresh with all current columns. This loses existing
   data, which is acceptable for development/demo databases but not for production data.
2. **Manually alter the table** with a raw `ALTER TABLE todo ADD COLUMN priority INTEGER
   DEFAULT 0` executed once against the existing file, preserving existing rows.

For projects that need to evolve their schema repeatedly without losing data, the standard
solution is **Flask-Migrate** (a wrapper around Alembic), which tracks schema changes as
versioned migration scripts and applies only the diff. Introducing it is a reasonable
suggestion for a growing project, but is more tooling than a small demo app typically needs.
