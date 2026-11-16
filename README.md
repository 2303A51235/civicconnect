# CivicConnect — Smart Public Complaint Management System

A Flask + SQLite civic issue reporting demo with citizen, staff and admin workflows; offline keyword-based category/priority suggestions; geocoded location search; interactive OpenStreetMap maps; and complaint editing.

## Features
- Citizen registration, login and complaint history
- Create and edit complaints (title, description, category, priority, photo and location)
- Explicit category selection or automatic category suggestion
- Priority selection or automatic priority suggestion
- Search places/addresses with OpenStreetMap Nominatim, use device location, click or drag a map pin, and reverse-geocode the selected point
- Complaint detail map with a popup describing the selected issue location
- Public complaint feed with search, category filtering and a map of all geolocated reports
- Complaint upvotes and activity timeline
- Admin dashboard and department staff status updates
- SQLite database created automatically on startup

## Run locally (Windows)
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create/activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   ```
4. Install dependencies and start:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
5. Open http://127.0.0.1:5000

You can also double-click `run.bat` on Windows.

## Demo accounts
- Admin: `admin@civicconnect.local` / `Admin@123`
- Staff: `staff@civicconnect.local` / `Staff@123`
- Citizen: register through the app.

Change demo passwords before sharing a public deployment.

## Deploy on Render
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python -c "from app import init_db; init_db()" && gunicorn app:app`
- Add environment variable `SECRET_KEY` with a long random value.

**Storage note:** SQLite and uploaded photos are stored locally. Render's free web service filesystem is ephemeral, so data and uploads may be lost on redeploy/restart. Use a persistent disk or managed database/object storage for production records.

## Location search notes
Place search and reverse geocoding use the public OpenStreetMap Nominatim service; map tiles use OpenStreetMap. These features require internet access and are subject to the provider's fair-use/rate limits. Browser geolocation requires permission and a secure context (localhost or HTTPS).

## AI note
The built-in classifier is an explainable keyword-based baseline, not a trained machine-learning model. It runs offline and can be replaced with a trained model later.
