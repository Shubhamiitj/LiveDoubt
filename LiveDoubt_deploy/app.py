from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "livedoubt.db")

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id=1),
            subject TEXT NOT NULL DEFAULT 'Fluid Mechanics',
            topic TEXT NOT NULL DEFAULT 'Convective Acceleration'
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO settings (id, subject, topic)
        VALUES (1, 'Fluid Mechanics', 'Convective Acceleration')
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS doubts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL,
            seat_no TEXT NOT NULL,
            subject TEXT NOT NULL,
            doubt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            priority TEXT NOT NULL DEFAULT 'normal',
            answer TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            answered_at TEXT DEFAULT ''
        )
    """)
    # Upgrade old database if it already exists
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(doubts)").fetchall()}
    if "priority" not in cols:
        conn.execute("ALTER TABLE doubts ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'")
    if "answer" not in cols:
        conn.execute("ALTER TABLE doubts ADD COLUMN answer TEXT DEFAULT ''")
    if "answered_at" not in cols:
        conn.execute("ALTER TABLE doubts ADD COLUMN answered_at TEXT DEFAULT ''")
    conn.commit()
    conn.close()

@app.route("/")
def student():
    return render_template("student.html")

@app.route("/professor")
def professor():
    return render_template("professor.html")

@app.get("/api/settings")
def get_settings():
    conn = get_conn()
    row = conn.execute("SELECT subject, topic FROM settings WHERE id=1").fetchone()
    conn.close()
    return jsonify(dict(row))

@app.post("/api/settings")
def update_settings():
    data = request.get_json() or {}
    subject = str(data.get("subject", "")).strip()
    topic = str(data.get("topic", "")).strip()
    if not subject or not topic:
        return jsonify({"ok": False, "error": "Subject and current topic are required."}), 400
    conn = get_conn()
    conn.execute("UPDATE settings SET subject=?, topic=? WHERE id=1", (subject, topic))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.post("/api/doubts")
def create_doubt():
    data = request.get_json() or {}
    required = ["roll_no", "seat_no", "doubt"]
    if not all(str(data.get(x, "")).strip() for x in required):
        return jsonify({"ok": False, "error": "Please fill roll number, seat number and doubt."}), 400

    conn = get_conn()
    settings = conn.execute("SELECT subject FROM settings WHERE id=1").fetchone()
    subject = str(settings["subject"]).strip()

    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("""
        INSERT INTO doubts
        (roll_no, seat_no, subject, doubt, status, priority, answer, created_at)
        VALUES (?, ?, ?, ?, 'new', 'normal', '', ?)
    """, (
        str(data["roll_no"]).strip(),
        str(data["seat_no"]).strip(),
        subject,
        str(data["doubt"]).strip(),
        now
    ))
    doubt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": doubt_id})

@app.get("/api/doubts")
def get_doubts():
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, roll_no, seat_no, subject, doubt, status, priority,
               answer, created_at, answered_at
        FROM doubts
        ORDER BY
            CASE WHEN status='new' THEN 0 ELSE 1 END,
            CASE WHEN priority='high' THEN 0 ELSE 1 END,
            id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.post("/api/doubts/<int:doubt_id>/priority")
def set_priority(doubt_id):
    data = request.get_json() or {}
    priority = data.get("priority", "normal")
    if priority not in ("high", "normal"):
        return jsonify({"ok": False, "error": "Invalid priority."}), 400
    conn = get_conn()
    conn.execute("UPDATE doubts SET priority=? WHERE id=?", (priority, doubt_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.post("/api/doubts/<int:doubt_id>/answer")
def answer_doubt(doubt_id):
    data = request.get_json() or {}
    answer = str(data.get("answer", "")).strip()
    if not answer:
        return jsonify({"ok": False, "error": "Answer cannot be empty."}), 400
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    cur = conn.execute("""
        UPDATE doubts
        SET answer=?, status='answered', answered_at=?
        WHERE id=?
    """, (answer, now, doubt_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": cur.rowcount > 0})

@app.post("/api/doubts/<int:doubt_id>/resolve")
def resolve(doubt_id):
    conn = get_conn()
    conn.execute("UPDATE doubts SET status='resolved' WHERE id=?", (doubt_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.get("/api/student/<roll_no>")
def student_doubts(roll_no):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, roll_no, seat_no, subject, doubt, status, priority,
               answer, created_at, answered_at
        FROM doubts
        WHERE roll_no=?
        ORDER BY id DESC
    """, (roll_no.strip(),)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.delete("/api/doubts/<int:doubt_id>")
def delete_doubt(doubt_id):
    data = request.get_json(silent=True) or {}
    roll_no = str(data.get("roll_no", "")).strip()

    if not roll_no:
        return jsonify({"ok": False, "error": "Roll number is required."}), 400

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM doubts WHERE id=? AND roll_no=?",
        (doubt_id, roll_no)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Doubt not found or not yours."}), 404

    conn.execute(
        "DELETE FROM doubts WHERE id=? AND roll_no=?",
        (doubt_id, roll_no)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# Initialize the database when Flask is started by Gunicorn or directly.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
