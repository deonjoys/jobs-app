# Jobs App

A Flask booking marketplace for construction and repair professionals.

## Deploy to Vercel

1. Push this repository to GitHub and import it into Vercel.
2. Create a hosted PostgreSQL database. The database must be reachable from
   Vercel and should use SSL if the provider requires it.
3. In **Vercel → Project → Settings → Environment Variables**, set these for
   Production (and Preview if needed):
   - `DATABASE_URL` — the PostgreSQL connection URL from your database provider.
   - `SECRET_KEY` — a long, random secret used to sign Flask sessions.
   - `ADMIN_PASSWORD` — the initial admin password. Change it to a strong,
     unique password before launch.
4. Redeploy after adding or changing environment variables.

Vercel detects Python 3.12 from `.python-version`, installs packages from
`requirements.txt`, and routes requests through `app.py` using `vercel.json`.
The app creates its tables on startup. On first startup it also creates the
admin account using `ADMIN_PASSWORD`; changing that environment variable later
does not reset an existing admin password.

Vercel's function filesystem is not persistent. Uploads are written to `/tmp`
so the upload flow can run, but files may disappear between function
invocations and are not durable. Configure object storage before relying on
worker photos or portfolio uploads in production.

## Run locally

Install dependencies with `pip install -r requirements.txt`, then run
`python app.py`. Without database environment variables, the app uses local
SQLite (`jobs.db`).

For local PostgreSQL, set `DATABASE_URL`, `SECRET_KEY`, and `ADMIN_PASSWORD`
in your shell before starting the app.
