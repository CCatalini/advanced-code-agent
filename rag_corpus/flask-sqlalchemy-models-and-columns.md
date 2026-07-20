# Defining models and columns with Flask-SQLAlchemy

Flask-SQLAlchemy models are plain Python classes that inherit from `db.Model`, where `db`
is the `SQLAlchemy` extension instance bound to the Flask app (`db = SQLAlchemy(app)`).
Each class attribute assigned to a `db.Column(...)` becomes a column in the underlying
table.

```python
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
```

Common column arguments:
- `nullable=False` — the database rejects rows without a value for that column.
- `default=...` — a Python-side default applied when a new object is created without
  explicitly setting that field. For mutable/callable defaults use a function reference
  (e.g. `default=datetime.utcnow`), not a called value, so it's evaluated per-row rather
  than once at class-definition time.
- `db.Column(db.Integer)` for numeric priority levels, `db.Column(db.String(N))` for short
  text, `db.Column(db.DateTime, nullable=True)` for optional dates such as a due date.

Adding a **new** column to an existing model is a Python-only change (the class gets a new
attribute) but it does **not** retroactively alter a database file that was already
created. See `flask-sqlalchemy-migrations-vs-create-all.md` for what that implies in
practice for a project without a migrations tool.
