# CivicConnect – Smart Public Complaint Management System

A locally runnable Flask + SQLite project for reporting and tracking civic complaints.

## Requirements
- Python 3.9 or newer
- Internet connection for OpenStreetMap tiles and Leaflet map assets (the rest of the app runs locally)

## Run on Windows
1. Extract the ZIP.
2. Open Command Prompt / PowerShell in the `CivicConnect` folder.
3. (Recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Open http://127.0.0.1:5000

The SQLite database is created automatically as `database.db`.

## Demo accounts
- Admin: `admin@civicconnect.local` / `Admin@123`
- Department staff: `staff@civicconnect.local` / `Staff@123`
- Citizen: create an account using Register.

Change the demo passwords and `SECRET_KEY` before any public deployment.

## Included functionality
- Citizen registration and login (hashed passwords)
- Submit complaints with description, optional photo and map-selected coordinates
- Offline keyword-based AI-assisted category, department and priority suggestions
- Public complaint list, search and category filter
- Complaint details, timeline and one-vote-per-citizen upvoting
- Admin dashboard with counts and charts
- Department staff dashboard
- Admin/staff status updates and department assignment
- SQLite persistence

## Notes
- The AI classifier is deliberately lightweight and runs locally without API keys or model downloads. It is a keyword-scoring baseline, not a trained predictive model. It can be replaced by a scikit-learn model later.
- Uploaded images are saved in `static/uploads/`. For production, use a managed object store and validate uploads more rigorously.
- This is an educational prototype, not an official government complaint service.
