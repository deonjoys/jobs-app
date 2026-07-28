# JobS

A booking marketplace for professional contracting &amp; repair workers —
masons, plumbers, painters, carpenters, interior decorators, and AC
installers. Clients browse verified pros and their portfolios and submit
booking requests; admins manage the full worker roster.

## Features

- **Client site** — browse by trade category or search by name, view a
  worker's photo, rate, experience, and portfolio gallery, then submit a
  booking request.
- **Admin — full worker CRUD**:
  - Add a worker with a profile picture and portfolio photos
  - Edit any worker's details, replace their photo, add more portfolio photos
  - Remove individual portfolio photos
  - Delete a worker entirely (also cleans up their uploaded files)
  - Confirm booking requests
- **Database-backed** — workers, portfolio photos, and bookings are all
  stored in PostgreSQL. Photos are saved to disk under `static/uploads/`
  and referenced by filename.

## Setup

1. Create the database:
   ```sql
   CREATE DATABASE jobs_db;
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) configure connection env vars — defaults assume local
   Postgres with user/password `postgres`:
   ```bash
   export DB_USER=postgres
   export DB_PASS=postgres
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=jobs_db
   export SECRET_KEY=change-me
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Visit:
   - Client site: http://127.0.0.1:5000/
   - Admin portal: http://127.0.0.1:5000/admin
   - Add a worker: http://127.0.0.1:5000/admin/workers/new

## Database schema

- `workers` — name, trade, phone, hourly_rate, experience_years, bio,
  status, photo_filename, created_at
- `portfolio_images` — worker_id (FK), filename, caption
- `bookings` — worker_id (FK), client_name, client_phone, service_address,
  booking_date, status

## Notes

- Uploaded images are capped at 16MB per request and restricted to
  png/jpg/jpeg/webp/gif.
- Tables auto-create on first run via `db.create_all()`. For production,
  swap this for a migration tool (e.g. Flask-Migrate/Alembic).
- For production, serve uploads from object storage (S3, etc.) rather
  than local disk, and set a real `SECRET_KEY`.
