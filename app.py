import os, sqlite3, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from ai.predict import predict_complaint

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-secret-key-for-production"),
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)

DEPARTMENTS = {
    "Roads": "Public Works Department",
    "Garbage": "Sanitation Department",
    "Water Leakage": "Water Department",
    "Streetlights": "Electricity Department",
    "Drainage": "Drainage Department",
    "Other": "General Services",
}

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'citizen',
        department TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        department TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Submitted',
        latitude REAL,
        longitude REAL,
        location_text TEXT,
        photo TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS upvotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        complaint_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, complaint_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(complaint_id) REFERENCES complaints(id)
    );
    CREATE TABLE IF NOT EXISTS complaint_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(complaint_id) REFERENCES complaints(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    # Demo accounts: admin and one staff account. Change passwords after first login.
    admin = db.execute("SELECT id FROM users WHERE email=?", ("admin@civicconnect.local",)).fetchone()
    if not admin:
        db.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                   ("CivicConnect Admin", "admin@civicconnect.local",
                    generate_password_hash("Admin@123"), "admin", datetime.now().isoformat(timespec="seconds")))
    staff = db.execute("SELECT id FROM users WHERE email=?", ("staff@civicconnect.local",)).fetchone()
    if not staff:
        db.execute("INSERT INTO users(name,email,password,role,department,created_at) VALUES(?,?,?,?,?,?)",
                   ("Roads Department Staff", "staff@civicconnect.local",
                    generate_password_hash("Staff@123"), "staff", "Public Works Department",
                    datetime.now().isoformat(timespec="seconds")))
    db.commit()
    db.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    db = get_db()
    stats = {
        "total": db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
        "resolved": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
        "open": db.execute("SELECT COUNT(*) FROM complaints WHERE status!='Resolved'").fetchone()[0],
        "areas": db.execute("SELECT COUNT(DISTINCT location_text) FROM complaints WHERE location_text IS NOT NULL AND location_text!=''").fetchone()[0],
    }
    complaints = db.execute("""
        SELECT c.*, u.name AS reporter,
        (SELECT COUNT(*) FROM upvotes v WHERE v.complaint_id=c.id) AS votes
        FROM complaints c JOIN users u ON u.id=c.user_id
        ORDER BY c.created_at DESC LIMIT 6
    """).fetchall()
    return render_template("index.html", stats=stats, complaints=complaints)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "danger")
            return render_template("register.html")
        try:
            get_db().execute(
                "INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                (name, email, generate_password_hash(password), "citizen", datetime.now().isoformat(timespec="seconds"))
            )
            get_db().commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"], department=user["department"])
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "staff":
        return redirect(url_for("staff_dashboard"))
    return redirect(url_for("my_complaints"))

@app.route("/complaints")
@login_required
def my_complaints():
    rows = get_db().execute("""
        SELECT c.*, (SELECT COUNT(*) FROM upvotes v WHERE v.complaint_id=c.id) AS votes
        FROM complaints c WHERE c.user_id=? ORDER BY c.created_at DESC
    """, (session["user_id"],)).fetchall()
    return render_template("my_complaints.html", complaints=rows)

@app.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if session.get("role") != "citizen":
        flash("Only citizen accounts can submit complaints.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location_text = request.form.get("location_text", "").strip()
        lat = request.form.get("latitude") or None
        lng = request.form.get("longitude") or None
        if not title or not description:
            flash("Title and description are required.", "danger")
            return render_template("report.html")
        prediction = predict_complaint(title + " " + description)
        photo_name = None
        photo = request.files.get("photo")
        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash("Please upload a JPG, PNG, WEBP or GIF image.", "danger")
                return render_template("report.html")
            safe_name = secure_filename(photo.filename)
            photo_name = f"{secrets.token_hex(8)}_{safe_name}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_name))
        now = datetime.now().isoformat(timespec="seconds")
        cursor = get_db().execute("""
            INSERT INTO complaints(user_id,title,description,category,department,priority,status,
            latitude,longitude,location_text,photo,created_at,updated_at)
            VALUES(?,?,?,?,?,?,'Submitted',?,?,?,?,?,?)
        """, (session["user_id"], title, description, prediction["category"], prediction["department"],
              prediction["priority"], lat, lng, location_text, photo_name, now, now))
        complaint_id = cursor.lastrowid
        get_db().execute(
            "INSERT INTO complaint_updates(complaint_id,user_id,status,note,created_at) VALUES(?,?,?,?,?)",
            (complaint_id, session["user_id"], "Submitted", "Complaint submitted by citizen.", now)
        )
        get_db().commit()
        flash(f"Complaint #{complaint_id} submitted. Suggested category: {prediction['category']}.", "success")
        return redirect(url_for("complaint_detail", complaint_id=complaint_id))
    return render_template("report.html")

@app.route("/complaints/<int:complaint_id>")
def complaint_detail(complaint_id):
    db = get_db()
    complaint = db.execute("""
        SELECT c.*, u.name AS reporter,
        (SELECT COUNT(*) FROM upvotes v WHERE v.complaint_id=c.id) AS votes
        FROM complaints c JOIN users u ON u.id=c.user_id WHERE c.id=?
    """, (complaint_id,)).fetchone()
    if not complaint:
        abort(404)
    if session.get("role") == "citizen" and complaint["user_id"] != session.get("user_id"):
        # Public complaints are viewable by everyone.
        pass
    history = db.execute("""
        SELECT cu.*, u.name AS actor FROM complaint_updates cu
        JOIN users u ON u.id=cu.user_id WHERE cu.complaint_id=? ORDER BY cu.created_at ASC
    """, (complaint_id,)).fetchall()
    voted = False
    if session.get("user_id"):
        voted = bool(db.execute("SELECT id FROM upvotes WHERE user_id=? AND complaint_id=?",
                                 (session["user_id"], complaint_id)).fetchone())
    return render_template("complaint_detail.html", complaint=complaint, history=history, voted=voted)

@app.route("/complaints/<int:complaint_id>/upvote", methods=["POST"])
@login_required
def upvote(complaint_id):
    if session.get("role") != "citizen":
        flash("Only citizens can upvote.", "warning")
        return redirect(url_for("complaint_detail", complaint_id=complaint_id))
    try:
        get_db().execute("INSERT INTO upvotes(user_id,complaint_id,created_at) VALUES(?,?,?)",
                         (session["user_id"], complaint_id, datetime.now().isoformat(timespec="seconds")))
        get_db().commit()
        flash("Your support has been counted.", "success")
    except sqlite3.IntegrityError:
        get_db().execute("DELETE FROM upvotes WHERE user_id=? AND complaint_id=?", (session["user_id"], complaint_id))
        get_db().commit()
        flash("Your upvote was removed.", "info")
    return redirect(url_for("complaint_detail", complaint_id=complaint_id))

@app.route("/public-complaints")
def public_complaints():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    sql = """SELECT c.*, u.name AS reporter,
             (SELECT COUNT(*) FROM upvotes v WHERE v.complaint_id=c.id) AS votes
             FROM complaints c JOIN users u ON u.id=c.user_id WHERE 1=1"""
    params = []
    if q:
        sql += " AND (c.title LIKE ? OR c.description LIKE ? OR c.location_text LIKE ?)"
        params += [f"%{q}%"] * 3
    if category:
        sql += " AND c.category=?"
        params.append(category)
    sql += " ORDER BY c.created_at DESC"
    rows = get_db().execute(sql, params).fetchall()
    return render_template("public_complaints.html", complaints=rows, q=q, category=category,
                           categories=list(DEPARTMENTS.keys()))

@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    db = get_db()
    stats = {
        "total": db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
        "submitted": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Submitted'").fetchone()[0],
        "progress": db.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'").fetchone()[0],
        "resolved": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users WHERE role='citizen'").fetchone()[0],
    }
    complaints = db.execute("""
        SELECT c.*, u.name AS reporter,
        (SELECT COUNT(*) FROM upvotes v WHERE v.complaint_id=c.id) AS votes
        FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY c.created_at DESC
    """).fetchall()
    category_rows = db.execute("SELECT category, COUNT(*) AS total FROM complaints GROUP BY category").fetchall()
    status_rows = db.execute("SELECT status, COUNT(*) AS total FROM complaints GROUP BY status").fetchall()
    return render_template("admin_dashboard.html", stats=stats, complaints=complaints,
                           category_data=[dict(r) for r in category_rows],
                           status_data=[dict(r) for r in status_rows], departments=sorted(set(DEPARTMENTS.values())))

@app.route("/staff")
@role_required("staff", "admin")
def staff_dashboard():
    db = get_db()
    if session.get("role") == "admin":
        rows = db.execute("SELECT c.*,u.name AS reporter FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY c.created_at DESC").fetchall()
    else:
        rows = db.execute("SELECT c.*,u.name AS reporter FROM complaints c JOIN users u ON u.id=c.user_id WHERE c.department=? ORDER BY c.created_at DESC",
                          (session.get("department"),)).fetchall()
    return render_template("staff_dashboard.html", complaints=rows)

@app.route("/admin/complaints/<int:complaint_id>/update", methods=["POST"])
@role_required("admin", "staff")
def update_complaint(complaint_id):
    db = get_db()
    complaint = db.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    if not complaint:
        abort(404)
    if session.get("role") == "staff" and complaint["department"] != session.get("department"):
        abort(403)
    status = request.form.get("status")
    department = request.form.get("department", complaint["department"])
    note = request.form.get("note", "").strip()
    allowed_status = {"Submitted", "Assigned", "In Progress", "Resolved", "Rejected"}
    if status not in allowed_status:
        abort(400)
    now = datetime.now().isoformat(timespec="seconds")
    db.execute("UPDATE complaints SET status=?,department=?,updated_at=? WHERE id=?",
               (status, department, now, complaint_id))
    db.execute("INSERT INTO complaint_updates(complaint_id,user_id,status,note,created_at) VALUES(?,?,?,?,?)",
               (complaint_id, session["user_id"], status, note or f"Status changed to {status}.", now))
    db.commit()
    flash(f"Complaint #{complaint_id} updated.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="The page or complaint could not be found."), 404

@app.errorhandler(413)
def too_large(error):
    flash("Image is too large. Maximum upload size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("new_complaint"))

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)
