# Flask routing and query parameters

Flask maps URL paths to Python functions ("view functions") using the `@app.route()`
decorator. A route can accept multiple HTTP methods by passing `methods=[...]`, and the
current method is available at runtime via `request.method`.

Dynamic segments in the path (e.g. `/update/<int:id>`) are passed as keyword arguments to
the view function, with Flask converting them according to the declared converter (`int`,
`string`, `float`, `path`, etc.). If the converter fails to match (e.g. a non-numeric id),
Flask returns a 404 automatically before the view function even runs.

Query string parameters (the part after `?` in a URL, e.g. `/todos?priority=high&sort=due_date`)
are **not** part of the route pattern. They are read inside the view function through
`request.args`, which behaves like a read-only dictionary (technically a `MultiDict`).
Common patterns:

```python
from flask import request

@app.route('/')
def index():
    priority = request.args.get('priority')          # None if absent
    sort_by = request.args.get('sort', 'date_created') # default value
    show_completed = request.args.get('completed', 'true') == 'true'
```

This is the standard way to implement filtering/sorting endpoints without creating a new
route per combination of filters: one route reads optional query params and adjusts the
database query accordingly. Contrast this with `request.form`, which reads data submitted
via an HTML form with `method="POST"`, and is unrelated to the URL's query string.

A common mistake is trying to read filter parameters from `request.form` on a `GET`
request — form data is only populated for the body of `POST`/`PUT` requests, so filtering
via a link (`GET`) must use `request.args`.
