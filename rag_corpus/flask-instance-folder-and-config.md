# The instance folder and SQLALCHEMY_DATABASE_URI

`app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'` tells Flask-SQLAlchemy
to use a SQLite file named `database.db`. A **relative** sqlite URI (three slashes) is
resolved by Flask relative to the app's `instance/` folder, not the current working
directory — Flask creates this folder automatically the first time it's needed
(`instance/database.db`).

This matters for two practical reasons:
1. When inspecting or backing up the real on-disk database, look inside `instance/`, not
   the project root.
2. The `instance/` folder is meant for environment-specific, non-version-controlled files
   (local databases, secrets), so it's a reasonable candidate for a deny-write policy
   pattern in a coding agent unless the task explicitly involves the database file.

An absolute URI (four slashes, `sqlite:////tmp/database.db`) bypasses the instance folder
entirely and is resolved as a literal filesystem path.
