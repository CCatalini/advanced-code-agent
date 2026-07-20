# Templates and Jinja2 basics

Flask renders HTML via `render_template('name.html', **context)`, looking for templates in
a `templates/` folder next to the app module. The templating engine is Jinja2, which
supports variable interpolation (`{{ variable }}`), control flow (`{% if %}`, `{% for %}`),
and template inheritance via `{% extends "base.html" %}` + `{% block content %}...{% endblock %}`.

For a list view that needs to display filter controls (e.g. a dropdown to filter tasks by
priority), the common pattern is to pass both the filtered items and the currently active
filter value into the template, so the template can mark the active option as selected and
build links that preserve the other query parameters:

```python
return render_template(
    'index.html',
    tasks=tasks,
    current_priority=request.args.get('priority'),
    current_sort=request.args.get('sort', 'date_created'),
)
```

```html
<select onchange="location.href='?priority=' + this.value">
  <option value="">All</option>
  <option value="1" {% if current_priority == '1' %}selected{% endif %}>Low</option>
  <option value="2" {% if current_priority == '2' %}selected{% endif %}>Medium</option>
  <option value="3" {% if current_priority == '3' %}selected{% endif %}>High</option>
</select>
```

Iterating over a query result in a template is the same as iterating over any Python
iterable: `{% for task in tasks %} ... {% endfor %}`.
