# Notes on scoping a code-change task safely (general guidance)

When a coding agent is asked to add a field to an existing data model plus a way to query
by it, a safe, minimal sequence of changes is:

1. Add the column to the model definition (see `flask-sqlalchemy-models-and-columns.md`).
2. Reconcile the on-disk schema with the new column — check whether the project uses
   migrations; if not, recreating the dev database is usually acceptable (see
   `flask-sqlalchemy-migrations-vs-create-all.md`).
3. Extend the relevant route(s) to accept optional query parameters and translate them into
   `.filter()`/`.order_by()` calls (see `flask-sqlalchemy-queries.md` and
   `flask-routing-and-query-params.md`), defaulting to the previous behavior when no filter
   is supplied, so existing links/bookmarks to the unfiltered view keep working.
4. Update the template to expose the new filter/sort controls without breaking the
   existing list rendering (see `flask-templates-and-jinja.md`).
5. Add or extend automated tests using the test client, covering both the new filtered
   behavior and a regression check that the existing unfiltered routes still behave as
   before (see `flask-testing-with-test-client.md`).

Keeping the new column optional (nullable, or with a sensible default) and the new query
parameters optional (falling back to today's behavior when absent) is what keeps this
change backward compatible with any existing callers of the same routes.
