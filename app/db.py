"""
AgentIA - SQLite Persistence Layer
Stores profiles, benchmarks, calendars, posts and cost tracking.
iRL-tech x EPINEXUS - Feb 2026
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).parent.parent / "data" / "agentia.db"


def _get_conn():
    """Get a SQLite connection with row_factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            persona_content TEXT NOT NULL,
            social_profile TEXT DEFAULT '',
            interview_messages TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            segment TEXT DEFAULT '',
            location TEXT DEFAULT '',
            experience TEXT DEFAULT '',
            platforms TEXT DEFAULT '[]',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS calendars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            calendar_content TEXT NOT NULL,
            start_date TEXT DEFAULT '',
            focus_theme TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            calendar_id INTEGER,
            platform TEXT DEFAULT '',
            format TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            content TEXT NOT NULL,
            model_used TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id),
            FOREIGN KEY (calendar_id) REFERENCES calendars(id)
        );

        CREATE TABLE IF NOT EXISTS cost_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS post_edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL UNIQUE,
            caption TEXT NOT NULL,
            hashtags TEXT DEFAULT '',
            cta TEXT DEFAULT '',
            image_path TEXT DEFAULT '',
            image_prompt TEXT DEFAULT '',
            platform_captions TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
    """)
    conn.commit()
    conn.close()


# --- PROFILES ---

def save_profile(agent_name, persona_content, social_profile="", interview_messages=None):
    """Save a profile, deactivating previous ones. Returns the new profile id."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    messages_json = json.dumps(interview_messages or [], ensure_ascii=False)

    # Deactivate all previous profiles
    conn.execute("UPDATE profiles SET is_active = 0, updated_at = ? WHERE is_active = 1", (now,))

    cursor = conn.execute(
        "INSERT INTO profiles (agent_name, persona_content, social_profile, interview_messages, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
        (agent_name, persona_content, social_profile, messages_json, now, now),
    )
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return profile_id


def get_active_profile():
    """Get the currently active profile as a dict, or None."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM profiles WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "agent_name": row["agent_name"],
        "persona_content": row["persona_content"],
        "social_profile": row["social_profile"],
        "interview_messages": json.loads(row["interview_messages"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_all_profiles():
    """Get all profiles ordered by creation date (newest first)."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM profiles ORDER BY id DESC").fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "agent_name": row["agent_name"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# --- BENCHMARKS ---

def save_benchmark(profile_id, segment, location, experience, platforms, content):
    """Save a benchmark report. Returns the new benchmark id."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    platforms_json = json.dumps(platforms or [], ensure_ascii=False)
    cursor = conn.execute(
        "INSERT INTO benchmarks (profile_id, segment, location, experience, platforms, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (profile_id, segment, location, experience, platforms_json, content, now, now),
    )
    benchmark_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return benchmark_id


def get_latest_benchmark(profile_id=None):
    """Get the most recent benchmark, optionally filtered by profile."""
    conn = _get_conn()
    if profile_id:
        row = conn.execute("SELECT * FROM benchmarks WHERE profile_id = ? ORDER BY id DESC LIMIT 1", (profile_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM benchmarks ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "profile_id": row["profile_id"],
        "segment": row["segment"],
        "location": row["location"],
        "experience": row["experience"],
        "platforms": json.loads(row["platforms"]),
        "content": row["content"],
        "created_at": row["created_at"],
    }


# --- CALENDARS ---

def save_calendar(profile_id, calendar_content, start_date="", focus_theme=""):
    """Save a calendar. Returns the new calendar id."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO calendars (profile_id, calendar_content, start_date, focus_theme, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (profile_id, calendar_content, str(start_date), focus_theme, now, now),
    )
    calendar_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return calendar_id


def get_latest_calendar(profile_id=None):
    """Get the most recent calendar, optionally filtered by profile."""
    conn = _get_conn()
    if profile_id:
        row = conn.execute("SELECT * FROM calendars WHERE profile_id = ? ORDER BY id DESC LIMIT 1", (profile_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM calendars ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "profile_id": row["profile_id"],
        "calendar_content": row["calendar_content"],
        "start_date": row["start_date"],
        "focus_theme": row["focus_theme"],
        "created_at": row["created_at"],
    }


# --- POSTS ---

def save_post(profile_id, platform, format_, topic, content, model_used, calendar_id=None):
    """Save a generated post. Returns the new post id."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO posts (profile_id, calendar_id, platform, format, topic, content, model_used, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (profile_id, calendar_id, platform, format_, topic, content, model_used, now),
    )
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_recent_posts(limit=10, profile_id=None):
    """Get recent posts, optionally filtered by profile."""
    conn = _get_conn()
    if profile_id:
        rows = conn.execute("SELECT * FROM posts WHERE profile_id = ? ORDER BY id DESC LIMIT ?", (profile_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM posts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "profile_id": row["profile_id"],
            "platform": row["platform"],
            "format": row["format"],
            "topic": row["topic"],
            "content": row["content"],
            "model_used": row["model_used"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_post_count(profile_id=None):
    """Get total number of posts."""
    conn = _get_conn()
    if profile_id:
        row = conn.execute("SELECT COUNT(*) as cnt FROM posts WHERE profile_id = ?", (profile_id,)).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) as cnt FROM posts").fetchone()
    conn.close()
    return row["cnt"]


# --- POST EDITS ---

def get_post_by_id(post_id: int):
    """Get a single post by its ID, or None."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "profile_id": row["profile_id"],
        "platform": row["platform"],
        "format": row["format"],
        "topic": row["topic"],
        "content": row["content"],
        "model_used": row["model_used"],
        "created_at": row["created_at"],
    }


def save_post_edit(post_id, caption, hashtags, cta, image_path="", image_prompt="", platform_captions=None):
    """Save or update an edit for a post (upsert). Returns the edit id."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    captions_json = json.dumps(platform_captions or {}, ensure_ascii=False)
    cursor = conn.execute(
        """INSERT OR REPLACE INTO post_edits
           (post_id, caption, hashtags, cta, image_path, image_prompt, platform_captions, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?,
                   COALESCE((SELECT created_at FROM post_edits WHERE post_id = ?), ?),
                   ?)""",
        (post_id, caption, hashtags, cta, image_path, image_prompt, captions_json, post_id, now, now),
    )
    edit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return edit_id


def get_post_edit(post_id: int):
    """Get the saved edit for a post, or None. Deserializes platform_captions JSON."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM post_edits WHERE post_id = ?", (post_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "post_id": row["post_id"],
        "caption": row["caption"],
        "hashtags": row["hashtags"],
        "cta": row["cta"],
        "image_path": row["image_path"],
        "image_prompt": row["image_prompt"],
        "platform_captions": json.loads(row["platform_captions"]) if row["platform_captions"] else {},
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_posts_for_editor(limit=50, profile_id=None, platform=None, search=None):
    """Get posts for the editor sidebar with has_edit flag.

    LEFT JOIN post_edits to add a has_edit boolean.
    Filters by profile_id, platform, and topic search.
    """
    conn = _get_conn()
    query = """
        SELECT p.id, p.platform, p.format, p.topic, p.created_at,
               CASE WHEN pe.id IS NOT NULL THEN 1 ELSE 0 END as has_edit
        FROM posts p
        LEFT JOIN post_edits pe ON pe.post_id = p.id
        WHERE 1=1
    """
    params = []

    if profile_id:
        query += " AND p.profile_id = ?"
        params.append(profile_id)
    if platform and platform != "Toutes":
        query += " AND p.platform = ?"
        params.append(platform)
    if search:
        query += " AND p.topic LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY p.id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "platform": row["platform"],
            "format": row["format"],
            "topic": row["topic"],
            "created_at": row["created_at"],
            "has_edit": bool(row["has_edit"]),
        }
        for row in rows
    ]


def get_edit_count():
    """Get total number of edited posts."""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM post_edits").fetchone()
    conn.close()
    return row["cnt"]


# --- COST TRACKING ---

def update_cost(input_tokens, output_tokens, estimated_cost):
    """Add cost tracking entry for today."""
    conn = _get_conn()
    today = date.today().isoformat()

    existing = conn.execute("SELECT id, input_tokens, output_tokens, estimated_cost FROM cost_tracking WHERE session_date = ?", (today,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE cost_tracking SET input_tokens = ?, output_tokens = ?, estimated_cost = ? WHERE id = ?",
            (existing["input_tokens"] + input_tokens, existing["output_tokens"] + output_tokens, existing["estimated_cost"] + estimated_cost, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO cost_tracking (session_date, input_tokens, output_tokens, estimated_cost) VALUES (?, ?, ?, ?)",
            (today, input_tokens, output_tokens, estimated_cost),
        )
    conn.commit()
    conn.close()


def get_total_cost():
    """Get total accumulated cost across all sessions."""
    conn = _get_conn()
    row = conn.execute("SELECT COALESCE(SUM(input_tokens), 0) as total_in, COALESCE(SUM(output_tokens), 0) as total_out, COALESCE(SUM(estimated_cost), 0.0) as total_cost FROM cost_tracking").fetchone()
    conn.close()
    return {
        "total_input_tokens": row["total_in"],
        "total_output_tokens": row["total_out"],
        "total_cost": row["total_cost"],
    }


# --- DASHBOARD SUMMARY ---

def get_dashboard_summary():
    """Get all dashboard data in a single call."""
    conn = _get_conn()

    # Active profile
    profile_row = conn.execute("SELECT id, agent_name, created_at FROM profiles WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    profile = None
    profile_id = None
    if profile_row:
        profile_id = profile_row["id"]
        profile = {
            "id": profile_row["id"],
            "agent_name": profile_row["agent_name"],
            "created_at": profile_row["created_at"],
        }

    # Latest benchmark
    benchmark = None
    if profile_id:
        bench_row = conn.execute("SELECT segment, location, experience, created_at FROM benchmarks WHERE profile_id = ? ORDER BY id DESC LIMIT 1", (profile_id,)).fetchone()
        if bench_row:
            benchmark = {
                "segment": bench_row["segment"],
                "location": bench_row["location"],
                "experience": bench_row["experience"],
                "created_at": bench_row["created_at"],
            }

    # Latest calendar
    calendar = None
    if profile_id:
        cal_row = conn.execute("SELECT id, start_date, focus_theme, created_at FROM calendars WHERE profile_id = ? ORDER BY id DESC LIMIT 1", (profile_id,)).fetchone()
        if cal_row:
            calendar = {
                "id": cal_row["id"],
                "start_date": cal_row["start_date"],
                "focus_theme": cal_row["focus_theme"],
                "created_at": cal_row["created_at"],
            }

    # Recent posts (3)
    recent_posts = []
    post_rows = conn.execute("SELECT platform, format, topic, created_at FROM posts ORDER BY id DESC LIMIT 3").fetchall()
    for row in post_rows:
        recent_posts.append({
            "platform": row["platform"],
            "format": row["format"],
            "topic": row["topic"],
            "created_at": row["created_at"],
        })

    # Post count
    post_count_row = conn.execute("SELECT COUNT(*) as cnt FROM posts").fetchone()
    post_count = post_count_row["cnt"]

    # Total cost
    cost_row = conn.execute("SELECT COALESCE(SUM(estimated_cost), 0.0) as total_cost FROM cost_tracking").fetchone()
    total_cost = cost_row["total_cost"]

    # Last activity
    last_activity = None
    for table in ["posts", "calendars", "benchmarks", "profiles"]:
        row = conn.execute(f"SELECT created_at FROM {table} ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            if not last_activity or row["created_at"] > last_activity:
                last_activity = row["created_at"]

    conn.close()

    return {
        "profile": profile,
        "benchmark": benchmark,
        "calendar": calendar,
        "recent_posts": recent_posts,
        "post_count": post_count,
        "total_cost": total_cost,
        "last_activity": last_activity,
    }
