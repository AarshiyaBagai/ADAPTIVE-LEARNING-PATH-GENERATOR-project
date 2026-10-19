"""SQLite storage: schema, connections and optional demo seed data."""
import json
import os
import sqlite3
from datetime import datetime, timezone

import security

_HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
  pw_hash     TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('student','senior','faculty')),
  name        TEXT NOT NULL,
  year        INTEGER,
  branch      TEXT,
  goal        TEXT,
  interests   TEXT NOT NULL DEFAULT '[]',
  avail       TEXT NOT NULL DEFAULT '[]',
  rep         INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_skills (
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill       TEXT NOT NULL,
  level       INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
  status      TEXT NOT NULL DEFAULT 'self' CHECK (status IN ('self','assessed','faculty')),
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (user_id, skill)
);

CREATE TABLE IF NOT EXISTS verify_requests (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill       TEXT NOT NULL,
  note        TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  created_at  TEXT NOT NULL,
  decided_by  INTEGER REFERENCES users(id),
  decided_at  TEXT
);
-- at most one open request per user and skill
CREATE UNIQUE INDEX IF NOT EXISTS ux_verify_pending ON verify_requests(user_id, skill) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS resources (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,
  type          TEXT NOT NULL,
  skill         TEXT NOT NULL,
  topic         TEXT NOT NULL,
  style         TEXT NOT NULL DEFAULT 'Read/Write',
  author_id     INTEGER NOT NULL REFERENCES users(id),
  base_rating_sum REAL NOT NULL DEFAULT 0,   -- seeded ratings (sum of stars)
  base_votes    INTEGER NOT NULL DEFAULT 0,
  base_users    INTEGER NOT NULL DEFAULT 0,  -- seeded outcome sample size
  base_gain     REAL NOT NULL DEFAULT 0,     -- seeded average score gain
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_ratings (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  PRIMARY KEY (resource_id, user_id)
);

-- measured effect: pre/post test score (0-10) of a student after using a resource
CREATE TABLE IF NOT EXISTS resource_outcomes (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  pre         INTEGER NOT NULL CHECK (pre BETWEEN 0 AND 10),
  post        INTEGER NOT NULL CHECK (post BETWEEN 0 AND 10),
  PRIMARY KEY (resource_id, user_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, resource_id)
);

CREATE TABLE IF NOT EXISTS questions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  body        TEXT NOT NULL,
  subject     TEXT NOT NULL,
  topic       TEXT NOT NULL,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  text        TEXT NOT NULL,
  votes       INTEGER NOT NULL DEFAULT 0,
  accepted    INTEGER NOT NULL DEFAULT 0,
  verified    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);
-- at most one accepted answer per question
CREATE UNIQUE INDEX IF NOT EXISTS ux_one_accepted ON answers(question_id) WHERE accepted = 1;

CREATE TABLE IF NOT EXISTS answer_votes (
  answer_id   INTEGER NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  PRIMARY KEY (answer_id, user_id)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str) -> None:
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------- demo seed ----------
# key in seed_demo.json -> login email. Only these accounts get the demo password.
DEMO_LOGINS = {
    "u1": "student@alpg.demo",
    "u2": "mentor@alpg.demo",
    "u3": "rohan@alpg.demo",
    "u4": "ananya@alpg.demo",
    "f1": "faculty@alpg.demo",
}
DEMO_PASSWORD = "demo123"


def seed_demo(path: str) -> bool:
    """Insert demo users, resources and questions once, into an empty database."""
    conn = connect(path)
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return False
        with open(os.path.join(_HERE, "seed_demo.json"), encoding="utf-8") as f:
            seed = json.load(f)
        demo_hash = security.hash_password(DEMO_PASSWORD)
        ts = now_iso()
        ids = {}
        for p in seed["people"]:
            email = DEMO_LOGINS.get(p["key"], f"{p['key']}@seed.invalid")
            pw = demo_hash if p["key"] in DEMO_LOGINS else "!"  # '!' = password login disabled
            cur = conn.execute(
                "INSERT INTO users (email, pw_hash, role, name, year, branch, goal, interests, avail, rep, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (email, pw, p["role"], p["name"], p["year"], p["branch"], p["goal"],
                 json.dumps(p["interests"]), json.dumps(p["avail"]), p["rep"], ts))
            ids[p["key"]] = cur.lastrowid
            for skill, level in p["skills"].items():
                conn.execute("INSERT INTO user_skills (user_id, skill, level, status, updated_at) VALUES (?,?,?,?,?)",
                             (cur.lastrowid, skill, level, p["status"].get(skill, "self"), ts))
        for r in seed["resources"]:
            conn.execute(
                "INSERT INTO resources (title, type, skill, topic, style, author_id, base_rating_sum, base_votes,"
                " base_users, base_gain, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (r["title"], r["type"], r["skill"], r["topic"], r["style"], ids[r["by"]],
                 r["rating"] * r["votes"], r["votes"], r["users"], r["gain"], ts))
        for q in seed["questions"]:
            cur = conn.execute(
                "INSERT INTO questions (title, body, subject, topic, user_id, created_at) VALUES (?,?,?,?,?,?)",
                (q["title"], q["body"], q["subject"], q["topic"], ids[q["by"]], ts))
            for a in q["answers"]:
                conn.execute(
                    "INSERT INTO answers (question_id, user_id, text, votes, accepted, verified, created_at)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (cur.lastrowid, ids[a["by"]], a["text"], a["votes"], int(a["accepted"]), int(a["verified"]), ts))
        conn.commit()
        return True
    finally:
        conn.close()
