# Testing Flask routes with the test client and pytest

Flask apps expose `app.test_client()`, a lightweight fake HTTP client that lets tests call
routes directly in-process, without starting a real server or making real network requests.

A typical `pytest` fixture pattern for an app that isn't built with the "app factory"
pattern (i.e. the `Flask(__name__)` instance is created at module import time, as in a
single-file `app.py`) is to import the already-created `app`/`db` objects and point the
database at a temporary file or in-memory SQLite for the duration of the test session:

```python
import pytest
from app import app, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()
```

Using `sqlite:///:memory:` avoids touching the real `instance/database.db` file and gives
each test run a clean schema created fresh from whatever the current model definitions are
— which sidesteps the schema-drift problem entirely for tests (see
`flask-sqlalchemy-migrations-vs-create-all.md`), since `create_all()` always builds the
in-memory database from the model as it exists right now.

Testing a route:

```python
def test_create_todo(client):
    response = client.post('/', data={'content': 'buy milk'}, follow_redirects=True)
    assert response.status_code == 200

def test_filter_by_priority(client):
    client.post('/', data={'content': 'urgent thing', 'priority': 3})
    response = client.get('/?priority=3')
    assert b'urgent thing' in response.data
```

`follow_redirects=True` is needed because routes that `return redirect('/')` after a
successful POST otherwise return a 302 response instead of the final page content.
