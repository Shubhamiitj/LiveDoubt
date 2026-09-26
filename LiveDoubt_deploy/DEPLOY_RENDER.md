# LiveDoubt — online deployment

This version is prepared for Render.

## Render settings
- Service type: Web Service
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Plan: Free (for testing/classroom prototype)

After deployment, students open the public HTTPS URL on their phones.
Professor opens the same URL with `/professor`.

## Important database note
This MVP uses SQLite. Render's default filesystem is ephemeral, so SQLite data is not suitable for permanent production storage. For a longer-term deployment, move the database to PostgreSQL or another managed datastore.
