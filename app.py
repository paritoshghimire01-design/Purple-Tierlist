from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "data.db")))
CATEGORIES = ["Crystal PvP", "Sword PvP", "Nethpot PvP", "Axe PvP", "Mace PvP"]
TIERS = ["S", "A", "B", "C", "D"]
ADMIN_SEED = [
    ("purple123", "hellofaabbccdd"),
    ("purple321", "hellofaabbccdd"),
]


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "purple-tier-secret-change-me")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: object | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            tier TEXT NOT NULL,
            avatar_url TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            player_name TEXT NOT NULL,
            category TEXT NOT NULL,
            tier TEXT NOT NULL,
            admin_username TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    now = datetime.utcnow().isoformat()
    for username, password in ADMIN_SEED:
        cursor.execute("SELECT id FROM admins WHERE username = ?", (username,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), now),
            )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_username"):
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


def validate_category(category: str) -> bool:
    return category in CATEGORIES


def validate_tier(tier: str) -> bool:
    return tier in TIERS


def player_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "tier": row["tier"],
        "avatarUrl": row["avatar_url"],
        "updatedAt": row["updated_at"],
    }


def add_audit_log(db: sqlite3.Connection, action: str, player_name: str, category: str, tier: str) -> None:
    db.execute(
        """
        INSERT INTO audit_logs (action, player_name, category, tier, admin_username, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            action,
            player_name,
            category,
            tier,
            session["admin_username"],
            datetime.utcnow().isoformat(),
        ),
    )


@app.get("/api/health")
def health() -> tuple[dict, int]:
    return {"status": "ok"}, 200


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    db = get_db()
    admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    if admin is None or not check_password_hash(admin["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["admin_username"] = admin["username"]
    return jsonify({"username": admin["username"], "role": "admin"})


@app.post("/api/logout")
@login_required
def logout():
    session.clear()
    return {"ok": True}, 200


@app.get("/api/session")
def session_status():
    username = session.get("admin_username")
    if not username:
        return {"authenticated": False}, 200
    return {"authenticated": True, "username": username, "role": "admin"}, 200


@app.get("/api/players")
def list_players():
    search = (request.args.get("search") or "").strip().lower()
    tier_filter = (request.args.get("tier") or "").strip()
    category_filter = (request.args.get("category") or "").strip()

    query = "SELECT * FROM players WHERE 1 = 1"
    params: list[str] = []

    if search:
        query += " AND LOWER(name) LIKE ?"
        params.append(f"%{search}%")
    if tier_filter and validate_tier(tier_filter):
        query += " AND tier = ?"
        params.append(tier_filter)
    if category_filter and validate_category(category_filter):
        query += " AND category = ?"
        params.append(category_filter)

    query += " ORDER BY category, CASE tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 WHEN 'C' THEN 4 ELSE 5 END, LOWER(name)"
    rows = get_db().execute(query, params).fetchall()

    grouped = {category: {tier: [] for tier in TIERS} for category in CATEGORIES}
    for row in rows:
        grouped[row["category"]][row["tier"]].append(player_to_dict(row))

    return jsonify({"categories": CATEGORIES, "tiers": TIERS, "players": grouped})


@app.post("/api/players")
@login_required
def create_player():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    tier = (payload.get("tier") or "").strip()
    avatar_url = (payload.get("avatarUrl") or "").strip() or None

    if not name:
        return {"error": "Player name is required"}, 400
    if not validate_category(category):
        return {"error": "Invalid category"}, 400
    if not validate_tier(tier):
        return {"error": "Invalid tier"}, 400

    now = datetime.utcnow().isoformat()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO players (name, category, tier, avatar_url, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, category, tier, avatar_url, now),
    )
    add_audit_log(db, "created", name, category, tier)
    db.commit()
    player = db.execute("SELECT * FROM players WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(player_to_dict(player)), 201


@app.put("/api/players/<int:player_id>")
@login_required
def update_player(player_id: int):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    existing = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    if existing is None:
        return {"error": "Player not found"}, 404

    name = (payload.get("name") or existing["name"]).strip()
    category = (payload.get("category") or existing["category"]).strip()
    tier = (payload.get("tier") or existing["tier"]).strip()
    avatar_url = payload.get("avatarUrl")
    avatar_url = existing["avatar_url"] if avatar_url is None else (avatar_url.strip() or None)

    if not name:
        return {"error": "Player name is required"}, 400
    if not validate_category(category):
        return {"error": "Invalid category"}, 400
    if not validate_tier(tier):
        return {"error": "Invalid tier"}, 400

    now = datetime.utcnow().isoformat()
    db.execute(
        """
        UPDATE players
        SET name = ?, category = ?, tier = ?, avatar_url = ?, updated_at = ?
        WHERE id = ?
        """,
        (name, category, tier, avatar_url, now, player_id),
    )
    add_audit_log(db, "updated", name, category, tier)
    db.commit()
    player = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    return jsonify(player_to_dict(player))


@app.delete("/api/players/<int:player_id>")
@login_required
def delete_player(player_id: int):
    db = get_db()
    existing = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    if existing is None:
        return {"error": "Player not found"}, 404

    db.execute("DELETE FROM players WHERE id = ?", (player_id,))
    add_audit_log(db, "deleted", existing["name"], existing["category"], existing["tier"])
    db.commit()
    return {"ok": True}, 200


@app.get("/api/logs")
def list_logs():
    rows = get_db().execute(
        """
        SELECT action, player_name, category, tier, admin_username, created_at
        FROM audit_logs
        ORDER BY datetime(created_at) DESC
        LIMIT 25
        """
    ).fetchall()
    is_admin = bool(session.get("admin_username"))
    return jsonify(
        [
            {
                "action": row["action"],
                "playerName": row["player_name"],
                "category": row["category"],
                "tier": row["tier"],
                "adminUsername": row["admin_username"] if is_admin else "Admin",
                "createdAt": row["created_at"],
            }
            for row in rows
        ]
    )


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/<path:path>")
def static_proxy(path: str):
    file_path = BASE_DIR / "static" / path
    if file_path.exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
