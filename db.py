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

-- ---------- phase 2: mentorship, projects, prep, planner ----------
CREATE TABLE IF NOT EXISTS grades (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  score   INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  PRIMARY KEY (user_id, subject)
);
CREATE TABLE IF NOT EXISTS mentor_profiles (
  user_id      INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  base_rating  REAL NOT NULL DEFAULT 0,
  base_mentees INTEGER NOT NULL DEFAULT 0,
  projects     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS student_profiles (
  user_id  INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  projects INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mentor_requests (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mentor_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  topic      TEXT NOT NULL,
  slot       TEXT NOT NULL,
  message    TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined')),
  pre        INTEGER CHECK (pre BETWEEN 0 AND 10),
  post       INTEGER CHECK (post BETWEEN 0 AND 10),
  created_at TEXT NOT NULL,
  decided_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_mentor_pending ON mentor_requests(student_id, mentor_id) WHERE status = 'pending';
CREATE TABLE IF NOT EXISTS projects (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      TEXT NOT NULL,
  descr      TEXT NOT NULL,
  needs      TEXT NOT NULL,
  tags       TEXT NOT NULL DEFAULT '[]',
  size       INTEGER NOT NULL CHECK (size BETWEEN 2 AND 6),
  timeline   TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','full')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_members (
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  joined_at  TEXT NOT NULL,
  PRIMARY KEY (project_id, user_id)
);
-- kind 'join' = the student asked, the owner decides; kind 'invite' = the owner asked, the student decides
CREATE TABLE IF NOT EXISTS project_requests (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       TEXT NOT NULL CHECK (kind IN ('join','invite')),
  status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined')),
  created_at TEXT NOT NULL,
  decided_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_project_pending ON project_requests(project_id, user_id) WHERE status = 'pending';
CREATE TABLE IF NOT EXISTS aptitude_sessions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  level      INTEGER NOT NULL,
  asked      TEXT NOT NULL DEFAULT '[]',
  current_q  TEXT,
  log        TEXT NOT NULL DEFAULT '[]',
  correct    INTEGER NOT NULL DEFAULT 0,
  done       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
-- first attempt at each technical question is the one that counts
CREATE TABLE IF NOT EXISTS tech_attempts (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  qid     TEXT NOT NULL,
  skill   TEXT NOT NULL,
  ok      INTEGER NOT NULL,
  PRIMARY KEY (user_id, qid)
);
CREATE TABLE IF NOT EXISTS coding_done (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  cid     TEXT NOT NULL,
  PRIMARY KEY (user_id, cid)
);
CREATE TABLE IF NOT EXISTS interview_answers (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  qidx     INTEGER NOT NULL,
  text     TEXT NOT NULL,
  score    INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text       TEXT NOT NULL,
  done       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_groups (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  goal         TEXT NOT NULL,
  skill        TEXT NOT NULL,
  base_members INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS group_members (
  group_id TEXT NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
  user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  PRIMARY KEY (group_id, user_id)
);
-- one row per user per active day; the streak is computed from these
CREATE TABLE IF NOT EXISTS activity (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day     TEXT NOT NULL,
  PRIMARY KEY (user_id, day)
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
        with open(os.path.join(_HERE, "content.json"), encoding="utf-8") as f:
            for g in json.load(f)["GROUPS"]:
                conn.execute("INSERT OR IGNORE INTO study_groups (id, name, goal, skill, base_members) VALUES (?,?,?,?,?)",
                             (g["id"], g["name"], g["goal"], g["skill"], g["members"]))
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
            if p["role"] == "senior":
                conn.execute("INSERT INTO mentor_profiles (user_id, base_rating, base_mentees, projects) VALUES (?,?,?,?)",
                             (cur.lastrowid, p.get("rating", 0), p.get("mentees", 0), p.get("projects", 0)))
            elif p["role"] == "student":
                conn.execute("INSERT INTO student_profiles (user_id, projects) VALUES (?,?)", (cur.lastrowid, p.get("projects", 0)))
            for subj, sc in p.get("grades", []):
                conn.execute("INSERT INTO grades (user_id, subject, score) VALUES (?,?,?)", (cur.lastrowid, subj, sc))
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
        for pr in seed.get("projects", []):
            cur = conn.execute(
                "INSERT INTO projects (owner_id, title, descr, needs, tags, size, timeline, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (ids[pr["owner"]], pr["title"], pr["desc"], json.dumps(pr["needs"]), json.dumps(pr["tags"]),
                 pr["size"], pr["timeline"], ts))
            conn.execute("INSERT INTO project_members (project_id, user_id, joined_at) VALUES (?,?,?)",
                         (cur.lastrowid, ids[pr["owner"]], ts))
        conn.execute("INSERT INTO group_members (group_id, user_id) VALUES ('g1', ?)", (ids["u1"],))
        conn.commit()
        return True
    finally:
        conn.close()
