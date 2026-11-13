# JobX

A Flask booking marketplace for construction and repair professionals.

## Deploy to Render

1. Push this repository to GitHub and select **New → Blueprint** in Render.
   Connect the repository and apply the settings in `render.yaml`.
2. The Blueprint creates a Python web service, PostgreSQL database, and a
   persistent disk for worker photos and portfolio media. These resources use
   paid Render plans; the disk is necessary because Render's service
   filesystem is otherwise temporary.
3. After the first deploy, open the web service's **Environment** page and
   retrieve the generated `ADMIN_PASSWORD`, or replace it with a strong
   password. Set a custom value before the first deploy if preferred. The
   generated `SECRET_KEY` and database connection are configured by the
   Blueprint.
4. Visit the service's `onrender.com` URL and sign in at `/admin/login`.
   Change the admin password after signing in if you used a generated value.

The app creates its database tables on startup. It creates the initial admin
account using `ADMIN_PASSWORD`; changing that environment variable later does
not reset an existing admin password. Keep the Render database and disk
attached when redeploying so records and uploads remain available.

Uploads accept images and videos and are limited to 16 MB per request.

## Run locally

Install dependencies with `pip install -r requirements.txt`, then run
`python app.py`. Without database environment variables, the app uses local
SQLite (`jobs.db`) and stores uploads in `static/uploads`.

For local PostgreSQL, set `DATABASE_URL`, `SECRET_KEY`, and `ADMIN_PASSWORD`
in your shell before starting the app. In production, the app requires those
secrets and a database URL rather than falling back to development defaults.
