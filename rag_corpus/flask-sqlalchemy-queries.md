# Querying, filtering and ordering with Flask-SQLAlchemy

Every model exposes a `.query` attribute (`Todo.query`) that returns a `Query` object,
which is built up lazily through chained method calls and only hits the database once you
call a terminal method like `.all()`, `.first()`, `.get()`, or iterate over it.

Common building blocks:

- `Todo.query.all()` — every row, no filtering.
- `Todo.query.filter_by(completed=False)` — equality filters using keyword arguments
  (only works for simple `column=value` comparisons).
- `Todo.query.filter(Todo.priority >= 2)` — the more general form, needed for comparisons
  other than equality (`>=`, `<=`, `!=`, `.in_(...)`, `.like(...)`).
- `.order_by(Todo.date_created)` ascending, `.order_by(Todo.priority.desc())` descending.
- `.get_or_404(id)` — fetch by primary key or automatically return a 404 response.

Filters and ordering can be chained and combined with optional query-string parameters
(see `flask-routing-and-query-params.md`):

```python
query = Todo.query
priority = request.args.get('priority')
if priority is not None:
    query = query.filter(Todo.priority == int(priority))

sort_by = request.args.get('sort', 'date_created')
sort_column = getattr(Todo, sort_by, Todo.date_created)
tasks = query.order_by(sort_column).all()
```

Building the query conditionally (only adding `.filter(...)` when a param was actually
provided) is the idiomatic way to support "optional" filters on a single route, instead of
writing a separate route per filter combination.

Note that `getattr(Todo, sort_by, ...)` when `sort_by` comes directly from user input
should be restricted to a known allow-list of sortable column names, to avoid exposing
internal columns or raising unexpected `AttributeError`s.
