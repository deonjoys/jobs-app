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

In the admin worker form, use **+ Add Photos** and **+ Add Videos** to select
multiple portfolio files. Local previews are shown immediately, and portfolio
media is saved as Data URLs in the database. Contractors' portfolio photos can
be opened in a lightbox, and videos play in the home-page Info modal. Portfolio
uploads are limited by the app's 16 MB request-size limit; storing Data URLs
increases database storage use.

Vercel's function filesystem is not persistent. Portfolio media is stored in
the database, but worker profile photos are still written to `/tmp` and may
disappear between function invocations. Configure object storage for durable
worker profile photos in production.

## Run locally

Install dependencies with `pip install -r requirements.txt`, then run
`python app.py`. Without database environment variables, the app uses local
SQLite (`jobs.db`).

For local PostgreSQL, set `DATABASE_URL`, `SECRET_KEY`, and `ADMIN_PASSWORD`
in your shell before starting the app.
