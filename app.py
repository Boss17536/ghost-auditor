"""
Ghost Auditor — Flask web application.
"""
import csv
import io
import json
import os
import threading
from collections import deque
from contextlib import redirect_stdout
from datetime import datetime

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key-12345")

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ghostauditor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# OAuth setup
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # Required for local debug
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID", "mock-client-id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "mock-client-secret"),
    scope=["profile", "email"],
    redirect_to="authorized"
)
app.register_blueprint(google_bp, url_prefix="/google")

# Encryption setup for API keys
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Use a static fallback for development if none provided. Needs 32 url-safe base64 bytes
    ENCRYPTION_KEY = b'xO0-vA9FhIwv7J-_pZ3W2zQXo-9aE80wO65hC3vQGk4='
fernet = Fernet(ENCRYPTION_KEY)

# DB Models
class User(db.Model):
    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(120))
    picture = db.Column(db.String(255))
    tinyfish_key = db.Column(db.String(255))
    workspace_url = db.Column(db.String(255))
    tool = db.Column(db.String(50), default="slack")
    seat_cost = db.Column(db.Float, default=7.00)
    last_audit_json = db.Column(db.Text)
    last_audit_date = db.Column(db.String(100))
    created_at = db.Column(db.String(100))

with app.app_context():
    db.create_all()

# Audit state
_audit_state = {
    "running": False,
    "log": deque(maxlen=100),
    "user_email": None
}
_audit_lock = threading.Lock()

def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    with _audit_lock:
        _audit_state["log"].append(f"[{ts}] {msg}")

def _run_audit_thread(user_email: str, app_context) -> None:
    with app_context:
        user = User.query.get(user_email)
        if not user:
            with _audit_lock: _audit_state["running"] = False
            return
        
        _log(f"Initializing audit for {user.tool.capitalize()} workspace: {user.workspace_url}")
        _heartbeat_stop = threading.Event()

        def _heartbeat():
            while not _heartbeat_stop.wait(5):
                with _audit_lock:
                    if _audit_state["running"]:
                        _log("[Agent] Still navigating and extracting data…")

        threading.Thread(target=_heartbeat, daemon=True).start()

        try:
            tf_key = fernet.decrypt(user.tinyfish_key.encode()).decode() if user.tinyfish_key else ""
            workspace = user.workspace_url
            tool = user.tool
            seat_cost = user.seat_cost

            from agent.slack_agent import audit_slack
            class LiveLogger:
                def write(self, data):
                    if data.strip(): _log(data.strip())
                def flush(self): pass

            with redirect_stdout(LiveLogger()):
                result = audit_slack(tf_key, workspace, tool, seat_cost)
            
            if result and result.get("status") == "SUCCESS" and result.get("members"):
                user.last_audit_json = json.dumps(result["members"])
                user.last_audit_date = datetime.now().isoformat()
                db.session.commit()
                _log(f"Audit complete! Discovered {len(result['members'])} total members.")
            else:
                _log("Agent failed to complete audit or returned no members.")

        except Exception as e:
            _log(f"Error during audit: {str(e)}")
        finally:
            _heartbeat_stop.set()
            with _audit_lock:
                _audit_state["running"] = False
                _audit_state["user_email"] = None

def get_current_user():
    if "email" in session:
        return User.query.get(session["email"])
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            info = resp.json()
            email = info["email"]
            name = info.get("name")
            picture = info.get("picture")
            
            user = User.query.get(email)
            if not user:
                user = User(email=email, name=name, picture=picture, created_at=datetime.now().isoformat())
                db.session.add(user)
                db.session.commit()
            
            session["email"] = email
            session["name"] = name
            session["picture"] = picture
            return user
    return None

@app.route("/")
def index():
    user = get_current_user()
    if user:
        if not user.tinyfish_key or not user.workspace_url:
            return redirect(url_for("onboarding"))
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/google/authorized")
def authorized():
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        tf_key = request.form.get("tinyfish_key")
        workspace = request.form.get("workspace_url")
        tool = request.form.get("tool", "slack")
        try:
            seat_cost = float(request.form.get("seat_cost", 7.00))
        except ValueError:
            seat_cost = 7.00
            
        if tf_key:
            user.tinyfish_key = fernet.encrypt(tf_key.encode()).decode()
        user.workspace_url = workspace
        user.tool = tool
        user.seat_cost = seat_cost
        db.session.commit()
        return redirect(url_for("dashboard"))
        
    return render_template("onboarding.html", user=user)

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))
    if not user.tinyfish_key or not user.workspace_url:
        return redirect(url_for("onboarding"))
    
    # Process members for stats
    members = []
    if user.last_audit_json:
        members = json.loads(user.last_audit_json)
        
    total_seats = len(members)
    inactive_count = sum(1 for m in members if m.get("is_inactive"))
    monthly_waste = inactive_count * user.seat_cost
    annual_waste = monthly_waste * 12
    
    return render_template(
        "dashboard.html",
        user=user,
        members=members,
        total_seats=total_seats,
        inactive_count=inactive_count,
        monthly_waste=monthly_waste,
        annual_waste=annual_waste,
        seat_cost=user.seat_cost
    )

@app.route("/settings", methods=["GET", "POST"])
def user_settings():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        tf_key = request.form.get("tinyfish_key")
        if tf_key and not tf_key.startswith("****"):
            user.tinyfish_key = fernet.encrypt(tf_key.encode()).decode()
            
        user.workspace_url = request.form.get("workspace_url")
        user.tool = request.form.get("tool", "slack")
        try:
            user.seat_cost = float(request.form.get("seat_cost", 7.00))
        except ValueError:
            pass
        db.session.commit()
        return redirect(url_for("dashboard"))
        
    masked_key = ""
    if user.tinyfish_key:
        try:
            decrypted = fernet.decrypt(user.tinyfish_key.encode()).decode()
            masked_key = f"****{decrypted[-4:]}" if len(decrypted) >= 4 else "****"
        except Exception:
            masked_key = "****"
            
    return render_template("settings.html", user=user, masked_key=masked_key)

@app.route("/audit", methods=["POST"])
def run_audit():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    with _audit_lock:
        if _audit_state["running"]:
            return jsonify({"status": "already_running"}), 202
        _audit_state["running"] = True
        _audit_state["user_email"] = user.email
        _audit_state["log"].clear()

    # Pass the app context to thread since SQLAlchemy requires it
    app_ctx = app.app_context()
    t = threading.Thread(target=_run_audit_thread, args=(user.email, app_ctx), daemon=True)
    t.start()
    return jsonify({"status": "started"}), 202

@app.route("/status")
def audit_status():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    with _audit_lock:
        is_my_audit = (_audit_state["user_email"] == user.email)
        running = _audit_state["running"] and is_my_audit
        log_snapshot = list(_audit_state["log"]) if is_my_audit else []
        
    members = []
    if not running:
        db.session.refresh(user)
        if user.last_audit_json:
            members = json.loads(user.last_audit_json)
            
    # Compute active counts
    inactive_ghosts = sum(1 for m in members if m.get("is_inactive"))
    monthly_wasted = inactive_ghosts * user.seat_cost
    
    return jsonify({
        "running": running, 
        "log": log_snapshot,
        "members": members,
        "total_provisioned": len(members),
        "inactive_ghosts": inactive_ghosts,
        "monthly_wasted": monthly_wasted,
        "annual_wasted": monthly_wasted * 12
    })

@app.route("/export")
def export_csv():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))
        
    members = []
    if user.last_audit_json:
        members = json.loads(user.last_audit_json)
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Last Active", "Role", "Status", "Wasted Cost / Mo"])
    for m in members:
        inactive = m.get("is_inactive", False)
        wasted = f"${user.seat_cost:.2f}" if inactive else "-"
        writer.writerow([
            m.get("name", ""),
            m.get("email", ""),
            m.get("last_active", "Never"),
            m.get("role", "Member"),
            "GHOST (30+ DAYS)" if inactive else "ACTIVE",
            wasted,
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ghost_auditor_report.csv"},
    )
    
if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
