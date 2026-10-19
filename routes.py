"""REST API for ALPG (phase-1 slice): auth, profile & skills, verification, pathway,
resources and Q&A. Handlers take a Ctx and return a payload or (status, payload)."""
import json
import re
import sqlite3
import sys
import threading
import time
import traceback

import db
import engine
import security
from db import now_iso

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
BRANCHES = ["CSE", "IT", "ECE", "Other"]
RESOURCE_TYPES = ["Notes", "Video", "Practice", "Article"]
LEARN_STYLES = ["Visual", "Auditory", "Read/Write", "Kinesthetic"]
MIN_SAMPLE_FOR_EFFECTIVENESS = 5
LOGIN_FAILS_BEFORE_LOCK = 5
LOGIN_LOCK_SECONDS = 60
MAX_BODY_BYTES = 1_000_000


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Ctx:
    def __init__(self, conn, user, params, query, body, ip, secret):
        self.conn, self.user, self.params = conn, user, params
        self.query, self.body, self.ip, self.secret = query, body, ip, secret


ROUTES = []  # (method, compiled regex, auth level, handler)


def route(method: str, pattern: str, auth: str = "user"):
    """auth: 'public' | 'user' (any signed-in account) | 'faculty'."""
    regex = pattern.replace("{id}", r"(?P<id>\d+)").replace("{key}", r"(?P<key>[a-z]{1,20})")
    compiled = re.compile("^" + regex + "$")

    def deco(fn):
        ROUTES.append((method, compiled, auth, fn))
        return fn
    return deco


# ---------- validation helpers ----------
def _bad(msg):
    return ApiError(400, "validation", msg)


def need_str(body, key, lo=1, hi=200, required=True):
    v = body.get(key)
    if v is None or v == "":
        if required:
            raise _bad(f"'{key}' is required")
        return None
    if not isinstance(v, str):
        raise _bad(f"'{key}' must be text")
    v = v.strip()
    if not (lo <= len(v) <= hi):
        raise _bad(f"'{key}' must be {lo}-{hi} characters")
    return v


def need_int(body, key, lo, hi, required=True):
    v = body.get(key)
    if v is None:
        if required:
            raise _bad(f"'{key}' is required")
        return None
    if isinstance(v, bool) or not isinstance(v, int):
        raise _bad(f"'{key}' must be a whole number")
    if not (lo <= v <= hi):
        raise _bad(f"'{key}' must be between {lo} and {hi}")
    return v


def need_choice(body, key, choices, required=True, default=None):
    v = body.get(key)
    if v is None or v == "":
        if required and default is None:
            raise _bad(f"'{key}' is required")
        return default
    if v not in choices:
        raise _bad(f"'{key}' must be one of: {', '.join(choices)}")
    return v


def need_str_list(body, key, max_items, max_len, allowed=None):
    v = body.get(key)
    if v is None:
        return None
    if not isinstance(v, list) or len(v) > max_items:
        raise _bad(f"'{key}' must be a list of at most {max_items} items")
    out = []
    for x in v:
        if not isinstance(x, str) or not (1 <= len(x.strip()) <= max_len):
            raise _bad(f"'{key}' items must be text of 1-{max_len} characters")
        x = x.strip()
        if allowed is not None and x not in allowed:
            raise _bad(f"'{key}' contains an invalid value: {x}")
        if x not in out:
            out.append(x)
    return out


def limit_param(ctx, default=50, cap=100):
    raw = ctx.query.get("limit")
    if raw is None:
        return default
    if not raw.isdigit() or int(raw) < 1:
        raise _bad("'limit' must be a positive whole number")
    return min(int(raw), cap)


# ---------- shared lookups ----------
def user_json(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"], "year": row["year"],
            "branch": row["branch"], "goal": row["goal"], "interests": json.loads(row["interests"]),
            "avail": json.loads(row["avail"]), "rep": row["rep"]}


def skills_of(conn, user_id) -> dict:
    rows = conn.execute("SELECT skill, level, status FROM user_skills WHERE user_id=?", (user_id,)).fetchall()
    return {r["skill"]: {"level": r["level"], "status": r["status"]} for r in rows}


def levels_of(conn, user_id) -> dict:
    return {k: v["level"] for k, v in skills_of(conn, user_id).items()}


def change_rep(conn, user_id, delta):
    conn.execute("UPDATE users SET rep = MAX(0, rep + ?) WHERE id=?", (delta, user_id))


def require_role(ctx, *roles):
    if ctx.user["role"] not in roles:
        raise ApiError(403, "forbidden", "Your account type cannot do this.")


def require_skill(key):
    if key not in engine.SKILLS:
        raise ApiError(404, "not_found", f"Unknown skill '{key}'.")


# ---------- public ----------
@route("GET", "/api/health", "public")
def health(ctx):
    return {"status": "ok", "time": now_iso()}


@route("GET", "/api/taxonomy", "public")
def taxonomy(ctx):
    return {
        "skills": {k: {"name": s["name"], "prereqs": s["pre"]} for k, s in engine.SKILLS.items()},
        "roles": {n: {"description": r["desc"], "required": r["req"]} for n, r in engine.ROLES.items()},
        "days": engine.DAYS, "branches": BRANCHES, "resource_types": RESOURCE_TYPES,
    }


# ---------- auth ----------
_FAILS = {}
_FAILS_LOCK = threading.Lock()


def _check_lock(key):
    with _FAILS_LOCK:
        e = _FAILS.get(key)
        if e and e["until"] > time.time():
            raise ApiError(429, "locked", f"Too many failed attempts. Try again in {int(e['until'] - time.time()) + 1} seconds.")


def _record_fail(key):
    with _FAILS_LOCK:
        if len(_FAILS) > 10000:  # bound memory: drop expired entries
            for k in [k for k, v in _FAILS.items() if v["until"] < time.time()]:
                del _FAILS[k]
        e = _FAILS.setdefault(key, {"n": 0, "until": 0})
        e["n"] += 1
        if e["n"] >= LOGIN_FAILS_BEFORE_LOCK:
            e["n"], e["until"] = 0, time.time() + LOGIN_LOCK_SECONDS


def _clear_fails(key):
    with _FAILS_LOCK:
        _FAILS.pop(key, None)


@route("POST", "/api/auth/register", "public")
def register(ctx):
    b = ctx.body
    name = need_str(b, "name", 2, 60)
    email = need_str(b, "email", 3, 120).lower()
    if not EMAIL_RE.match(email):
        raise _bad("Enter a valid email address.")
    password = b.get("password")
    if not isinstance(password, str) or not (8 <= len(password) <= 128):
        raise _bad("Password must be 8-128 characters.")
    year = need_int(b, "year", 1, 4, required=False) or 3
    branch = need_choice(b, "branch", BRANCHES, required=False, default="CSE")
    goal = need_choice(b, "goal", list(engine.ROLES), required=False, default="ML Engineer")
    try:
        # the role is never taken from the request: public sign-up always creates a student
        cur = ctx.conn.execute(
            "INSERT INTO users (email, pw_hash, role, name, year, branch, goal, interests, avail, rep, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (email, security.hash_password(password), "student", name, year, branch, goal, "[]",
             json.dumps(["Mon eve", "Wed eve"]), 0, now_iso()))
    except sqlite3.IntegrityError:
        raise ApiError(409, "email_taken", "An account with this email already exists.")
    row = ctx.conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return 201, {"token": security.make_token(ctx.secret, row["id"], row["role"]), "user": user_json(row)}


@route("POST", "/api/auth/login", "public")
def login(ctx):
    email = need_str(ctx.body, "email", 1, 120).lower()
    password = ctx.body.get("password")
    if not isinstance(password, str) or not password or len(password) > 128:
        raise _bad("'password' is required")
    key = (ctx.ip, email)
    _check_lock(key)
    row = ctx.conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    # verify against a dummy hash when the email is unknown, so timing does not reveal which emails exist
    ok = security.verify_password(password, row["pw_hash"] if row else security.DUMMY_HASH)
    if not row or not ok:
        _record_fail(key)
        raise ApiError(401, "bad_credentials", "Incorrect email or password.")
    _clear_fails(key)
    return {"token": security.make_token(ctx.secret, row["id"], row["role"]), "user": user_json(row)}


@route("GET", "/api/auth/me")
def me(ctx):
    return {"user": user_json(ctx.user), "skills": skills_of(ctx.conn, ctx.user["id"])}


# ---------- profile & skills ----------
@route("PUT", "/api/profile")
def update_profile(ctx):
    b, sets, vals = ctx.body, [], []
    if "goal" in b:
        sets.append("goal=?"); vals.append(need_choice(b, "goal", list(engine.ROLES)))
    if "year" in b:
        sets.append("year=?"); vals.append(need_int(b, "year", 1, 4))
    if "branch" in b:
        sets.append("branch=?"); vals.append(need_choice(b, "branch", BRANCHES))
    if "name" in b:
        sets.append("name=?"); vals.append(need_str(b, "name", 2, 60))
    if "interests" in b:
        sets.append("interests=?"); vals.append(json.dumps(need_str_list(b, "interests", 10, 30)))
    if "avail" in b:
        sets.append("avail=?"); vals.append(json.dumps(need_str_list(b, "avail", 7, 20, allowed=engine.DAYS)))
    if not sets:
        raise _bad("Nothing to update.")
    ctx.conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", (*vals, ctx.user["id"]))
    row = ctx.conn.execute("SELECT * FROM users WHERE id=?", (ctx.user["id"],)).fetchone()
    return user_json(row)


@route("PUT", "/api/skills/{key}")
def set_skill(ctx):
    """Set your own level (0 removes the skill). Raising a level always resets its evidence to
    'self': verification covers the level that was checked, not a higher self-claimed one."""
    require_role(ctx, "student", "senior")
    key = ctx.params["key"]
    require_skill(key)
    level = need_int(ctx.body, "level", 0, 5)
    uid = ctx.user["id"]
    row = ctx.conn.execute("SELECT level, status FROM user_skills WHERE user_id=? AND skill=?", (uid, key)).fetchone()
    if level == 0:
        ctx.conn.execute("DELETE FROM user_skills WHERE user_id=? AND skill=?", (uid, key))
    elif row is None:
        ctx.conn.execute("INSERT INTO user_skills (user_id, skill, level, status, updated_at) VALUES (?,?,?,?,?)",
                         (uid, key, level, "self", now_iso()))
    else:
        status = "self" if level > row["level"] else row["status"]
        ctx.conn.execute("UPDATE user_skills SET level=?, status=?, updated_at=? WHERE user_id=? AND skill=?",
                         (level, status, now_iso(), uid, key))
    return {"skills": skills_of(ctx.conn, uid)}


@route("POST", "/api/skills/{key}/verify-request")
def request_verification(ctx):
    require_role(ctx, "student", "senior")
    key = ctx.params["key"]
    require_skill(key)
    uid = ctx.user["id"]
    row = ctx.conn.execute("SELECT status FROM user_skills WHERE user_id=? AND skill=?", (uid, key)).fetchone()
    if row is None:
        raise _bad("Add this skill to your profile before requesting verification.")
    if row["status"] == "faculty":
        raise ApiError(409, "already_verified", "This skill is already faculty-verified.")
    note = need_str(ctx.body, "note", 0, 300, required=False) or ""
    try:
        cur = ctx.conn.execute("INSERT INTO verify_requests (user_id, skill, note, created_at) VALUES (?,?,?,?)",
                               (uid, key, note, now_iso()))
    except sqlite3.IntegrityError:
        raise ApiError(409, "already_pending", "A verification request for this skill is already pending.")
    return 201, {"id": cur.lastrowid, "skill": key, "status": "pending"}


@route("GET", "/api/verify/queue", "faculty")
def verify_queue(ctx):
    rows = ctx.conn.execute(
        "SELECT v.id, v.skill, v.note, v.created_at, u.id AS user_id, u.name, s.level, s.status"
        " FROM verify_requests v JOIN users u ON u.id=v.user_id"
        " LEFT JOIN user_skills s ON s.user_id=v.user_id AND s.skill=v.skill"
        " WHERE v.status='pending' ORDER BY v.id").fetchall()
    return {"items": [{"id": r["id"], "user": {"id": r["user_id"], "name": r["name"]}, "skill": r["skill"],
                       "skill_name": engine.SKILLS[r["skill"]]["name"], "level": r["level"],
                       "current_status": r["status"], "note": r["note"], "created_at": r["created_at"]} for r in rows]}


def _decide(ctx, decision):
    vid = int(ctx.params["id"])
    v = ctx.conn.execute("SELECT * FROM verify_requests WHERE id=?", (vid,)).fetchone()
    if v is None:
        raise ApiError(404, "not_found", "Verification request not found.")
    if v["status"] != "pending":
        raise ApiError(409, "already_decided", "This request was already decided.")
    if decision == "approved":
        cur = ctx.conn.execute("UPDATE user_skills SET status='faculty', updated_at=? WHERE user_id=? AND skill=?",
                               (now_iso(), v["user_id"], v["skill"]))
        if cur.rowcount == 0:
            raise ApiError(409, "skill_removed", "The student no longer lists this skill.")
    ctx.conn.execute("UPDATE verify_requests SET status=?, decided_by=?, decided_at=? WHERE id=?",
                     (decision, ctx.user["id"], now_iso(), vid))
    return {"id": vid, "status": decision}


@route("POST", "/api/verify/{id}/approve", "faculty")
def verify_approve(ctx):
    return _decide(ctx, "approved")


@route("POST", "/api/verify/{id}/reject", "faculty")
def verify_reject(ctx):
    return _decide(ctx, "rejected")


# ---------- pathway & readiness ----------
def _role_param(ctx):
    role = ctx.query.get("role") or ctx.user["goal"]
    if not role:
        raise _bad("Choose a role (?role=...) or set a goal on your profile.")
    if role not in engine.ROLES:
        raise _bad(f"Unknown role '{role}'.")
    return role


@route("GET", "/api/pathway")
def get_pathway(ctx):
    role = _role_param(ctx)
    levels = levels_of(ctx.conn, ctx.user["id"])
    rd = engine.readiness(levels, engine.ROLES[role]["req"])
    return {"role": role, "readiness": rd["pct"], "gaps": engine.gap_list(levels, role),
            "steps": engine.pathway(levels, role)}


@route("GET", "/api/readiness")
def get_readiness(ctx):
    role = _role_param(ctx)
    rd = engine.readiness(levels_of(ctx.conn, ctx.user["id"]), engine.ROLES[role]["req"])
    return {"role": role, "source": "role", "pct": rd["pct"], "rows": rd["rows"]}


@route("POST", "/api/readiness/analyze")
def analyze_job(ctx):
    jd = need_str(ctx.body, "job_description", 1, 8000)
    found = engine.extract_skills(jd)
    levels = levels_of(ctx.conn, ctx.user["id"])
    if found:
        req, source = found, "job_description"
    else:  # nothing recognised: fall back to a role template
        role = need_choice(ctx.body, "role", list(engine.ROLES), required=False, default=ctx.user["goal"] or "ML Engineer")
        req, source = engine.ROLES[role]["req"], "role"
    rd = engine.readiness(levels, req)
    return {"source": source, "skills_found": sorted(found), "pct": rd["pct"], "rows": rd["rows"]}


# ---------- resources ----------
def _resource_query(conn, uid):
    return conn.execute("""
        SELECT r.*, u.name AS author_name,
          (SELECT COUNT(*) FROM resource_ratings x WHERE x.resource_id=r.id) AS n_rate,
          (SELECT COALESCE(SUM(rating),0) FROM resource_ratings x WHERE x.resource_id=r.id) AS sum_rate,
          (SELECT COUNT(*) FROM resource_outcomes o WHERE o.resource_id=r.id) AS n_out,
          (SELECT COALESCE(SUM(post-pre),0) FROM resource_outcomes o WHERE o.resource_id=r.id) AS sum_delta,
          (SELECT rating FROM resource_ratings x WHERE x.resource_id=r.id AND x.user_id=?) AS my_rating,
          EXISTS(SELECT 1 FROM bookmarks b WHERE b.resource_id=r.id AND b.user_id=?) AS bookmarked
        FROM resources r JOIN users u ON u.id=r.author_id""", (uid, uid)).fetchall()


def _resource_json(r, relevance=0.0) -> dict:
    votes = r["base_votes"] + r["n_rate"]
    users = r["base_users"] + r["n_out"]
    gain = (r["base_gain"] * r["base_users"] + r["sum_delta"]) / users if users else 0.0
    return {"id": r["id"], "title": r["title"], "type": r["type"], "skill": r["skill"],
            "skill_name": engine.SKILLS[r["skill"]]["name"], "topic": r["topic"], "style": r["style"],
            "author": {"id": r["author_id"], "name": r["author_name"]},
            "rating": round((r["base_rating_sum"] + r["sum_rate"]) / votes, 2) if votes else 0, "votes": votes,
            "users": users, "gain": round(gain, 2),
            # an average over a handful of students is noise, so effectiveness needs a minimum sample
            "effective": users >= MIN_SAMPLE_FOR_EFFECTIVENESS,
            "fills_gap": relevance > 0, "bookmarked": bool(r["bookmarked"]), "my_rating": r["my_rating"]}


def _one_resource(conn, rid, uid):
    for r in _resource_query(conn, uid):
        if r["id"] == rid:
            return _resource_json(r)
    raise ApiError(404, "not_found", "Resource not found.")


@route("GET", "/api/resources")
def list_resources(ctx):
    q = (ctx.query.get("q") or "").strip()[:100]
    skill, rtype = ctx.query.get("skill"), ctx.query.get("type")
    sort = ctx.query.get("sort", "rel")
    if sort not in ("rel", "eff", "rating"):
        raise _bad("'sort' must be rel, eff or rating")
    if skill and skill not in engine.SKILLS:
        raise _bad("Unknown skill filter.")
    if rtype and rtype not in RESOURCE_TYPES:
        raise _bad("Unknown type filter.")
    goal = ctx.user["goal"]
    relevance = engine.gap_relevance(levels_of(ctx.conn, ctx.user["id"]), goal) if goal else {}
    items = []
    for r in _resource_query(ctx.conn, ctx.user["id"]):
        if skill and r["skill"] != skill:
            continue
        if rtype and r["type"] != rtype:
            continue
        score = 1
        if q:
            score = engine.search_score(q, f"{r['title']} {r['topic']} {engine.SKILLS[r['skill']]['name']} {r['type']}")
            if score <= 0:
                continue
        rel = relevance.get(r["skill"], 0.0)
        j = _resource_json(r, rel)
        items.append((score, engine.resource_rank_score(rel, j["gain"]), j))
    if sort == "eff":
        items.sort(key=lambda x: (-x[2]["gain"], x[2]["id"]))
    elif sort == "rating":
        items.sort(key=lambda x: (-x[2]["rating"], x[2]["id"]))
    else:
        items.sort(key=lambda x: (-x[0], -x[1], x[2]["id"]))
    out = [x[2] for x in items][:limit_param(ctx)]
    return {"count": len(out), "items": out}


@route("POST", "/api/resources")
def create_resource(ctx):
    b = ctx.body
    title = need_str(b, "title", 3, 120)
    rtype = need_choice(b, "type", RESOURCE_TYPES)
    skill = need_choice(b, "skill", list(engine.SKILLS))
    topic = need_str(b, "topic", 2, 60)
    style = need_choice(b, "style", LEARN_STYLES, required=False, default="Read/Write")
    cur = ctx.conn.execute(
        "INSERT INTO resources (title, type, skill, topic, style, author_id, created_at) VALUES (?,?,?,?,?,?,?)",
        (title, rtype, skill, topic, style, ctx.user["id"], now_iso()))
    change_rep(ctx.conn, ctx.user["id"], 5)
    return 201, _one_resource(ctx.conn, cur.lastrowid, ctx.user["id"])


def _resource_for_action(ctx):
    rid = int(ctx.params["id"])
    row = ctx.conn.execute("SELECT author_id FROM resources WHERE id=?", (rid,)).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Resource not found.")
    return rid, row["author_id"]


@route("POST", "/api/resources/{id}/rate")
def rate_resource(ctx):
    rid, author = _resource_for_action(ctx)
    if author == ctx.user["id"]:
        raise ApiError(403, "forbidden", "You cannot rate your own resource.")
    stars = need_int(ctx.body, "rating", 1, 5)
    ctx.conn.execute("INSERT INTO resource_ratings (resource_id, user_id, rating) VALUES (?,?,?)"
                     " ON CONFLICT(resource_id, user_id) DO UPDATE SET rating=excluded.rating",
                     (rid, ctx.user["id"], stars))
    return _one_resource(ctx.conn, rid, ctx.user["id"])


@route("POST", "/api/resources/{id}/bookmark")
def toggle_bookmark(ctx):
    rid, _ = _resource_for_action(ctx)
    uid = ctx.user["id"]
    cur = ctx.conn.execute("DELETE FROM bookmarks WHERE user_id=? AND resource_id=?", (uid, rid))
    if cur.rowcount == 0:
        ctx.conn.execute("INSERT INTO bookmarks (user_id, resource_id) VALUES (?,?)", (uid, rid))
    return {"bookmarked": cur.rowcount == 0}


@route("POST", "/api/resources/{id}/outcome")
def record_outcome(ctx):
    """Record your pre/post test score (0-10) around using a resource. These feed 'effectiveness'."""
    require_role(ctx, "student", "senior")
    rid, author = _resource_for_action(ctx)
    if author == ctx.user["id"]:
        raise ApiError(403, "forbidden", "You cannot record an outcome for your own resource.")
    pre, post = need_int(ctx.body, "pre", 0, 10), need_int(ctx.body, "post", 0, 10)
    ctx.conn.execute("INSERT INTO resource_outcomes (resource_id, user_id, pre, post) VALUES (?,?,?,?)"
                     " ON CONFLICT(resource_id, user_id) DO UPDATE SET pre=excluded.pre, post=excluded.post",
                     (rid, ctx.user["id"], pre, post))
    return _one_resource(ctx.conn, rid, ctx.user["id"])


# ---------- Q&A ----------
def _question_rows(conn):
    return conn.execute("""
        SELECT q.*, u.name AS author_name,
          (SELECT COUNT(*) FROM answers a WHERE a.question_id=q.id) AS n_answers,
          EXISTS(SELECT 1 FROM answers a WHERE a.question_id=q.id AND a.accepted=1) AS has_accepted,
          EXISTS(SELECT 1 FROM answers a WHERE a.question_id=q.id AND a.verified=1) AS has_verified
        FROM questions q JOIN users u ON u.id=q.user_id""").fetchall()


def _question_json(q) -> dict:
    return {"id": q["id"], "title": q["title"], "body": q["body"], "subject": q["subject"], "topic": q["topic"],
            "author": {"id": q["user_id"], "name": q["author_name"]}, "created_at": q["created_at"],
            "answers": q["n_answers"], "accepted": bool(q["has_accepted"]), "verified": bool(q["has_verified"])}


@route("GET", "/api/questions")
def list_questions(ctx):
    q = (ctx.query.get("q") or "").strip()[:100]
    items = []
    for r in _question_rows(ctx.conn):
        score = 1
        if q:
            score = engine.search_score(q, f"{r['title']} {r['body']} {r['topic']} {r['subject']}")
            if score <= 0:
                continue
        items.append((score, r["id"], _question_json(r)))
    items.sort(key=lambda x: (-x[0], -x[1]))
    out = [x[2] for x in items][:limit_param(ctx)]
    return {"count": len(out), "items": out}


@route("GET", "/api/questions/similar")
def similar_questions(ctx):
    title = (ctx.query.get("title") or "").strip()[:150]
    if len(title) < 3:
        return {"items": []}
    hits = [(engine.search_score(title, f"{r['title']} {r['topic']}"), r) for r in _question_rows(ctx.conn)]
    hits = sorted([h for h in hits if h[0] > 1], key=lambda h: -h[0])[:3]
    return {"items": [_question_json(r) for _, r in hits]}


@route("POST", "/api/questions")
def ask_question(ctx):
    b = ctx.body
    title, body = need_str(b, "title", 5, 150), need_str(b, "body", 5, 2000)
    subject, topic = need_str(b, "subject", 2, 60), need_str(b, "topic", 2, 60)
    cur = ctx.conn.execute("INSERT INTO questions (title, body, subject, topic, user_id, created_at) VALUES (?,?,?,?,?,?)",
                           (title, body, subject, topic, ctx.user["id"], now_iso()))
    row = [r for r in _question_rows(ctx.conn) if r["id"] == cur.lastrowid][0]
    return 201, _question_json(row)


@route("GET", "/api/questions/{id}")
def get_question(ctx):
    qid = int(ctx.params["id"])
    rows = [r for r in _question_rows(ctx.conn) if r["id"] == qid]
    if not rows:
        raise ApiError(404, "not_found", "Question not found.")
    answers = ctx.conn.execute(
        "SELECT a.*, u.name AS author_name FROM answers a JOIN users u ON u.id=a.user_id WHERE a.question_id=?"
        " ORDER BY a.accepted DESC, a.votes DESC, a.id", (qid,)).fetchall()
    voted = {r["answer_id"] for r in ctx.conn.execute(
        "SELECT answer_id FROM answer_votes WHERE user_id=?", (ctx.user["id"],)).fetchall()}
    out = _question_json(rows[0])
    out["is_asker"] = rows[0]["user_id"] == ctx.user["id"]
    out["answer_list"] = [{"id": a["id"], "text": a["text"], "votes": a["votes"], "accepted": bool(a["accepted"]),
                           "verified": bool(a["verified"]), "created_at": a["created_at"], "i_voted": a["id"] in voted,
                           "author": {"id": a["user_id"], "name": a["author_name"]}} for a in answers]
    return out


@route("POST", "/api/questions/{id}/answers")
def post_answer(ctx):
    qid = int(ctx.params["id"])
    if ctx.conn.execute("SELECT 1 FROM questions WHERE id=?", (qid,)).fetchone() is None:
        raise ApiError(404, "not_found", "Question not found.")
    text = need_str(ctx.body, "text", 2, 3000)
    cur = ctx.conn.execute("INSERT INTO answers (question_id, user_id, text, created_at) VALUES (?,?,?,?)",
                           (qid, ctx.user["id"], text, now_iso()))
    change_rep(ctx.conn, ctx.user["id"], 3)
    return 201, {"id": cur.lastrowid, "question_id": qid}


def _answer_for_action(ctx):
    aid = int(ctx.params["id"])
    row = ctx.conn.execute("SELECT a.*, q.user_id AS asker_id FROM answers a JOIN questions q ON q.id=a.question_id"
                           " WHERE a.id=?", (aid,)).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Answer not found.")
    return row


@route("POST", "/api/answers/{id}/vote")
def vote_answer(ctx):
    a = _answer_for_action(ctx)
    if a["user_id"] == ctx.user["id"]:
        raise ApiError(403, "forbidden", "You cannot vote on your own answer.")
    try:
        ctx.conn.execute("INSERT INTO answer_votes (answer_id, user_id) VALUES (?,?)", (a["id"], ctx.user["id"]))
    except sqlite3.IntegrityError:
        raise ApiError(409, "already_voted", "You already voted on this answer.")
    ctx.conn.execute("UPDATE answers SET votes = votes + 1 WHERE id=?", (a["id"],))
    change_rep(ctx.conn, a["user_id"], 2)
    return {"id": a["id"], "votes": a["votes"] + 1}


@route("POST", "/api/answers/{id}/accept")
def accept_answer(ctx):
    a = _answer_for_action(ctx)
    if a["asker_id"] != ctx.user["id"]:
        raise ApiError(403, "forbidden", "Only the person who asked can accept an answer.")
    if a["accepted"]:
        return {"id": a["id"], "accepted": True}
    prev = ctx.conn.execute("SELECT id, user_id FROM answers WHERE question_id=? AND accepted=1", (a["question_id"],)).fetchone()
    if prev:  # move the accepted mark; the earlier author loses the bonus
        ctx.conn.execute("UPDATE answers SET accepted=0 WHERE id=?", (prev["id"],))
        if prev["user_id"] != a["asker_id"]:
            change_rep(ctx.conn, prev["user_id"], -15)
    ctx.conn.execute("UPDATE answers SET accepted=1 WHERE id=?", (a["id"],))
    if a["user_id"] != a["asker_id"]:  # no reputation for accepting your own answer
        change_rep(ctx.conn, a["user_id"], 15)
    return {"id": a["id"], "accepted": True}


@route("POST", "/api/answers/{id}/verify", "faculty")
def verify_answer(ctx):
    a = _answer_for_action(ctx)
    if not a["verified"]:
        ctx.conn.execute("UPDATE answers SET verified=1 WHERE id=?", (a["id"],))
        change_rep(ctx.conn, a["user_id"], 10)
    return {"id": a["id"], "verified": True}


# ---------- dispatcher ----------
def dispatch(method, path, query, raw_body, headers, ip, db_path, secret):
    """Run one API request. Returns (status, json_payload, extra_headers)."""
    conn = None
    try:
        matched_path = False
        for m, regex, auth, fn in ROUTES:
            mt = regex.match(path)
            if not mt:
                continue
            matched_path = True
            if m != method:
                continue
            body = {}
            if method in ("POST", "PUT"):
                if len(raw_body) > MAX_BODY_BYTES:
                    raise ApiError(413, "too_large", "Request body is too large.")
                if raw_body.strip():
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        raise ApiError(400, "bad_json", "Request body must be valid JSON.")
                    if not isinstance(body, dict):
                        raise ApiError(400, "bad_json", "Request body must be a JSON object.")
            conn = db.connect(db_path)
            user = None
            if auth != "public":
                auth_header = headers.get("Authorization", "")
                payload = security.read_token(secret, auth_header[7:]) if auth_header.startswith("Bearer ") else None
                if payload:
                    user = conn.execute("SELECT * FROM users WHERE id=?", (int(payload["sub"]),)).fetchone()
                if user is None:
                    raise ApiError(401, "unauthorized", "Please sign in.")
                if auth == "faculty" and user["role"] != "faculty":
                    raise ApiError(403, "forbidden", "Faculty access only.")
            ctx = Ctx(conn, user, mt.groupdict(), query, body, ip, secret)
            result = fn(ctx)
            conn.commit()
            status, payload = result if isinstance(result, tuple) else (200, result)
            return status, payload, {}
        if matched_path:
            raise ApiError(405, "method_not_allowed", "Method not allowed for this route.")
        raise ApiError(404, "not_found", "No such API route.")
    except ApiError as e:
        if conn:
            conn.rollback()
        extra = {"Retry-After": str(LOGIN_LOCK_SECONDS)} if e.status == 429 else {}
        return e.status, {"error": {"code": e.code, "message": e.message}}, extra
    except Exception:
        if conn:
            conn.rollback()
        traceback.print_exc(file=sys.stderr)
        return 500, {"error": {"code": "server_error", "message": "Something went wrong on the server."}}, {}
    finally:
        if conn:
            conn.close()
