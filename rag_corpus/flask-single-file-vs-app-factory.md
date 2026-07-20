# Single-file app vs. the application factory pattern

Small Flask projects (and most tutorials) define everything at module level in a single
`app.py`: `app = Flask(__name__)`, the models, and the routes all live in one file, and the
module-level `app`/`db` objects are imported directly wherever needed (as in
`init_db.py: from app import app, db`).

This is simple and fine for small projects, but has two consequences worth knowing:
- There is exactly one `app`/`db` instance per Python process — you cannot easily spin up
  multiple independently-configured instances (e.g. one per test), only reconfigure the
  single instance's `app.config` before use, as shown in
  `flask-testing-with-test-client.md`.
- All routes and models are visible in one file, so understanding "the architecture" of
  such a project is mostly a matter of reading that one file top to bottom, rather than
  tracing imports across a package.

The alternative — the **application factory pattern** (`def create_app(): ...` returning a
configured `Flask` instance) — is recommended by Flask's own docs for larger projects
because it allows creating multiple app instances with different configs (crucial for
testing) and avoids circular imports between blueprints. Migrating a single-file app to a
factory is a legitimate refactor suggestion, but is a larger, riskier change than adding a
column and a filter route, and isn't necessary to implement a scoped feature.
