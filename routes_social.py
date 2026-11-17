"""Phase 2a: mentorship and project teams."""
import json
import sqlite3

import engine
from db import now_iso
from routes import (ApiError, route, need_str, need_int, need_str_list, require_role, levels_of, skills_of)


def person(conn, row) -> dict:
    """The fields the matching engine needs about one user."""
    prof = conn.execute("SELECT projects FROM student_profiles WHERE user_id=?", (row["id"],)).fetchone()
    mp = conn.execute("SELECT projects FROM mentor_profiles WHERE user_id=?", (row["id"],)).fetchone()
    return {"id": row["id"], "name": row["name"], "role": row["role"], "year": row["year"], "branch": row["branch"],
            "goal": row["goal"], "skills": levels_of(conn, row["id"]), "interests": json.loads(row["interests"]),
            "avail": json.loads(row["avail"]),
            "projects": (prof or mp)["projects"] if (prof or mp) else 0}


def _public(p: dict) -> dict:
    """What other students may see about a person: no email, no grades."""
    return {"id": p["id"], "name": p["name"], "year": p["year"], "branch": p["branch"], "goal": p["goal"],
            "skills": p["skills"], "interests": p["interests"], "avail": p["avail"], "projects": p["projects"]}


def _get_or_404(conn, table, rid, what):
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if row is None:
        raise ApiError(404, "not_found", f"{what} not found.")
    return row


def _names(conn):
    return {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM users").fetchall()}


# ======================= mentorship =======================
def _mentor_stats(conn, mid, mp):
    acc = conn.execute("SELECT COUNT(*) FROM mentor_requests WHERE mentor_id=? AND status='accepted'", (mid,)).fetchone()[0]
    gains = conn.execute("SELECT AVG(post-pre) FROM mentor_requests WHERE mentor_id=? AND pre IS NOT NULL", (mid,)).fetchone()[0]
    return {"rating": mp["base_rating"] if mp else 0, "mentees": (mp["base_mentees"] if mp else 0) + acc,
            "avg_gain": round(gains, 2) if gains is not None else None}


@route("GET", "/api/mentors")
def list_mentors(ctx):
    """Seniors ranked for the signed-in student, with the reason behind each score."""
    require_role(ctx, "student")
    me = person(ctx.conn, ctx.user)
    out = []
    for r in ctx.conn.execute("SELECT * FROM users WHERE role='senior'").fetchall():
        m = person(ctx.conn, r)
        mp = ctx.conn.execute("SELECT * FROM mentor_profiles WHERE user_id=?", (r["id"],)).fetchone()
        out.append({**_public(m), "stats": _mentor_stats(ctx.conn, r["id"], mp), "match": engine.mentor_match(m, me)})
    out.sort(key=lambda x: (-x["match"]["score"], x["id"]))
    return {"mentors": out}


def _req_json(r, names):
    return {"id": r["id"], "student": {"id": r["student_id"], "name": names.get(r["student_id"])},
            "mentor": {"id": r["mentor_id"], "name": names.get(r["mentor_id"])}, "topic": r["topic"], "slot": r["slot"],
            "message": r["message"], "status": r["status"], "pre": r["pre"], "post": r["post"],
            "created_at": r["created_at"]}


@route("GET", "/api/mentor-requests")
def list_mentor_requests(ctx):
    """Students see the requests they sent; seniors see the ones addressed to them. Nobody sees anyone else's."""
    col = "student_id" if ctx.user["role"] == "student" else "mentor_id" if ctx.user["role"] == "senior" else None
    if col is None:
        raise ApiError(403, "forbidden", "Your account type has no mentor requests.")
    rows = ctx.conn.execute(f"SELECT * FROM mentor_requests WHERE {col}=? ORDER BY id DESC", (ctx.user["id"],)).fetchall()
    names = _names(ctx.conn)
    return {"requests": [_req_json(r, names) for r in rows]}


@route("POST", "/api/mentor-requests")
def create_mentor_request(ctx):
    require_role(ctx, "student")
    mid = need_int(ctx.body, "mentor_id", 1, 10**9)
    topic = need_str(ctx.body, "topic", 2, 80)
    slot = need_str(ctx.body, "slot", 2, 30)
    msg = need_str(ctx.body, "message", 0, 500, required=False) or ""
    mentor = ctx.conn.execute("SELECT * FROM users WHERE id=? AND role='senior'", (mid,)).fetchone()
    if mentor is None:
        raise ApiError(404, "not_found", "Mentor not found.")
    if slot not in engine.DAYS:
        raise ApiError(400, "validation", "'slot' must be one of: " + ", ".join(engine.DAYS))
    try:
        cur = ctx.conn.execute(
            "INSERT INTO mentor_requests (student_id, mentor_id, topic, slot, message, created_at) VALUES (?,?,?,?,?,?)",
            (ctx.user["id"], mid, topic, slot, msg, now_iso()))
    except sqlite3.IntegrityError:
        raise ApiError(409, "conflict", "You already have an open request with this mentor.")
    r = ctx.conn.execute("SELECT * FROM mentor_requests WHERE id=?", (cur.lastrowid,)).fetchone()
    return 201, {"request": _req_json(r, _names(ctx.conn))}


def _decide_mentor(ctx, status):
    r = _get_or_404(ctx.conn, "mentor_requests", int(ctx.params["id"]), "Request")
    if r["mentor_id"] != ctx.user["id"]:
        raise ApiError(403, "forbidden", "Only the mentor this request was sent to can answer it.")
    # conditional update: two quick clicks cannot decide the same request twice
    cur = ctx.conn.execute("UPDATE mentor_requests SET status=?, decided_at=? WHERE id=? AND status='pending'",
                           (status, now_iso(), r["id"]))
    if cur.rowcount == 0:
        raise ApiError(409, "conflict", "This request has already been answered.")
    r = ctx.conn.execute("SELECT * FROM mentor_requests WHERE id=?", (r["id"],)).fetchone()
    return {"request": _req_json(r, _names(ctx.conn))}


@route("POST", "/api/mentor-requests/{id}/accept")
def accept_mentor_request(ctx):
    return _decide_mentor(ctx, "accepted")


@route("POST", "/api/mentor-requests/{id}/decline")
def decline_mentor_request(ctx):
    return _decide_mentor(ctx, "declined")


@route("POST", "/api/mentor-requests/{id}/outcome")
def mentor_outcome(ctx):
    """The student records a before/after score (0-10) once, after the mentor accepted."""
    r = _get_or_404(ctx.conn, "mentor_requests", int(ctx.params["id"]), "Request")
    if r["student_id"] != ctx.user["id"]:
        raise ApiError(403, "forbidden", "Only the student who made the request can record the result.")
    pre = need_int(ctx.body, "pre", 0, 10)
    post = need_int(ctx.body, "post", 0, 10)
    cur = ctx.conn.execute("UPDATE mentor_requests SET pre=?, post=? WHERE id=? AND status='accepted' AND pre IS NULL",
                           (pre, post, r["id"]))
    if cur.rowcount == 0:
        raise ApiError(409, "conflict", "The result can only be recorded once, after the mentor has accepted.")
    r = ctx.conn.execute("SELECT * FROM mentor_requests WHERE id=?", (r["id"],)).fetchone()
    return {"request": _req_json(r, _names(ctx.conn)), "gain": post - pre}


# ======================= projects and teams =======================
def _project_json(conn, p, viewer_id=None) -> dict:
    members = [r["user_id"] for r in conn.execute(
        "SELECT user_id FROM project_members WHERE project_id=? ORDER BY joined_at, user_id", (p["id"],)).fetchall()]
    names = _names(conn)
    return {"id": p["id"], "title": p["title"], "description": p["descr"], "owner": {"id": p["owner_id"], "name": names[p["owner_id"]]},
            "needs": json.loads(p["needs"]), "tags": json.loads(p["tags"]), "size": p["size"], "timeline": p["timeline"],
            "status": p["status"], "members": [{"id": m, "name": names[m]} for m in members],
            "seats_left": p["size"] - len(members), "is_member": viewer_id in members, "is_owner": viewer_id == p["owner_id"]}


@route("GET", "/api/projects")
def list_projects(ctx):
    rows = ctx.conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    return {"projects": [_project_json(ctx.conn, p, ctx.user["id"]) for p in rows]}


@route("POST", "/api/projects")
def create_project(ctx):
    require_role(ctx, "student")
    title = need_str(ctx.body, "title", 3, 80)
    desc = need_str(ctx.body, "description", 3, 600)
    needs = need_str_list(ctx.body, "needs", 8, 20, allowed=list(engine.SKILLS))
    if not needs:
        raise ApiError(400, "validation", "Pick at least one skill the project needs.")
    tags = need_str_list(ctx.body, "tags", 6, 30) or []
    size = need_int(ctx.body, "size", 2, 6)
    timeline = need_str(ctx.body, "timeline", 0, 40, required=False) or ""
    ts = now_iso()
    cur = ctx.conn.execute(
        "INSERT INTO projects (owner_id, title, descr, needs, tags, size, timeline, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (ctx.user["id"], title, desc, json.dumps(needs), json.dumps(tags), size, timeline, ts))
    ctx.conn.execute("INSERT INTO project_members (project_id, user_id, joined_at) VALUES (?,?,?)",
                     (cur.lastrowid, ctx.user["id"], ts))
    p = ctx.conn.execute("SELECT * FROM projects WHERE id=?", (cur.lastrowid,)).fetchone()
    return 201, {"project": _project_json(ctx.conn, p, ctx.user["id"])}


@route("GET", "/api/projects/{id}")
def get_project(ctx):
    """Anyone can read a project. Only its owner also gets the ranked candidates and the suggested team."""
    p = _get_or_404(ctx.conn, "projects", int(ctx.params["id"]), "Project")
    out = {"project": _project_json(ctx.conn, p, ctx.user["id"])}
    if p["owner_id"] == ctx.user["id"]:
        proj = {"needs": json.loads(p["needs"]), "tags": json.loads(p["tags"]), "size": p["size"]}
        owner = person(ctx.conn, ctx.user)
        member_ids = {m["id"] for m in out["project"]["members"]}
        cands = [person(ctx.conn, r) for r in ctx.conn.execute("SELECT * FROM users WHERE role='student'").fetchall()
                 if r["id"] not in member_ids]
        ranked = engine.rank_candidates(cands, proj, owner["avail"])
        members_skills = [levels_of(ctx.conn, m) for m in member_ids]
        sug = engine.suggest_team(ranked, proj, members_skills) if out["project"]["seats_left"] > 0 else \
            {"team": [], "covered": [], "missing": proj["needs"]}
        pend = {r["user_id"]: r["kind"] for r in ctx.conn.execute(
            "SELECT user_id, kind FROM project_requests WHERE project_id=? AND status='pending'", (p["id"],)).fetchall()}
        slim = lambda c: {**_public(c), "match": c["match"], "pending": pend.get(c["id"])}
        out["candidates"] = [slim(c) for c in ranked]
        out["suggested"] = {"team": [slim(c) for c in sug["team"]], "covered": sug["covered"], "missing": sug["missing"]}
    return out


@route("DELETE", "/api/projects/{id}")
def delete_project(ctx):
    p = _get_or_404(ctx.conn, "projects", int(ctx.params["id"]), "Project")
    if p["owner_id"] != ctx.user["id"]:
        raise ApiError(403, "forbidden", "Only the owner can delete a project.")
    ctx.conn.execute("DELETE FROM projects WHERE id=?", (p["id"],))
    return {"deleted": p["id"]}


def _open_project(ctx, pid):
    p = _get_or_404(ctx.conn, "projects", pid, "Project")
    if p["status"] == "full":
        raise ApiError(409, "full", "This project's team is already full.")
    return p


def _new_request(ctx, pid, uid, kind):
    if ctx.conn.execute("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (pid, uid)).fetchone():
        raise ApiError(409, "conflict", "Already a member of this project.")
    try:
        cur = ctx.conn.execute("INSERT INTO project_requests (project_id, user_id, kind, created_at) VALUES (?,?,?,?)",
                               (pid, uid, kind, now_iso()))
    except sqlite3.IntegrityError:
        raise ApiError(409, "conflict", "There is already a pending request for this project and student.")
    return 201, {"request": {"id": cur.lastrowid, "project_id": pid, "user_id": uid, "kind": kind, "status": "pending"}}


@route("POST", "/api/projects/{id}/join")
def request_join(ctx):
    require_role(ctx, "student")
    p = _open_project(ctx, int(ctx.params["id"]))
    return _new_request(ctx, p["id"], ctx.user["id"], "join")


@route("POST", "/api/projects/{id}/invite")
def invite(ctx):
    p = _open_project(ctx, int(ctx.params["id"]))
    if p["owner_id"] != ctx.user["id"]:
        raise ApiError(403, "forbidden", "Only the owner can invite people.")
    uid = need_int(ctx.body, "user_id", 1, 10**9)
    if ctx.conn.execute("SELECT 1 FROM users WHERE id=? AND role='student'", (uid,)).fetchone() is None:
        raise ApiError(404, "not_found", "Student not found.")
    return _new_request(ctx, p["id"], uid, "invite")


@route("GET", "/api/project-requests")
def list_project_requests(ctx):
    """'to_decide' = requests waiting for me (join requests on my projects, invitations to me); 'sent' = mine."""
    uid = ctx.user["id"]
    rows = ctx.conn.execute(
        "SELECT r.*, p.title, p.owner_id FROM project_requests r JOIN projects p ON p.id=r.project_id"
        " WHERE r.user_id=? OR p.owner_id=? ORDER BY r.id DESC", (uid, uid)).fetchall()
    names = _names(ctx.conn)
    to_decide, sent = [], []
    for r in rows:
        item = {"id": r["id"], "project": {"id": r["project_id"], "title": r["title"]}, "kind": r["kind"],
                "status": r["status"], "student": {"id": r["user_id"], "name": names[r["user_id"]]}}
        decider = r["owner_id"] if r["kind"] == "join" else r["user_id"]
        initiator = r["user_id"] if r["kind"] == "join" else r["owner_id"]
        if decider == uid and r["status"] == "pending":
            to_decide.append(item)
        if initiator == uid:
            sent.append(item)
    return {"to_decide": to_decide, "sent": sent}


def _decide_project(ctx, accept):
    r = _get_or_404(ctx.conn, "project_requests", int(ctx.params["id"]), "Request")
    p = ctx.conn.execute("SELECT * FROM projects WHERE id=?", (r["project_id"],)).fetchone()
    decider = p["owner_id"] if r["kind"] == "join" else r["user_id"]
    if decider != ctx.user["id"]:
        raise ApiError(403, "forbidden", "This request is not yours to answer.")
    if r["status"] != "pending":
        raise ApiError(409, "conflict", "This request has already been answered.")
    if accept:
        # One statement: the seat check and the insert cannot be separated, so two people accepted at the same
        # moment can never overfill the team.
        try:
            cur = ctx.conn.execute(
                "INSERT INTO project_members (project_id, user_id, joined_at)"
                " SELECT ?, ?, ? WHERE (SELECT COUNT(*) FROM project_members WHERE project_id=?) <"
                " (SELECT size FROM projects WHERE id=?)",
                (p["id"], r["user_id"], now_iso(), p["id"], p["id"]))
        except sqlite3.IntegrityError:
            raise ApiError(409, "conflict", "Already a member of this project.")
        if cur.rowcount == 0:
            raise ApiError(409, "full", "The team is already full.")
        ctx.conn.execute(
            "UPDATE projects SET status='full' WHERE id=? AND (SELECT COUNT(*) FROM project_members WHERE project_id=?) >= size",
            (p["id"], p["id"]))
    ctx.conn.execute("UPDATE project_requests SET status=?, decided_at=? WHERE id=?",
                     ("accepted" if accept else "declined", now_iso(), r["id"]))
    p = ctx.conn.execute("SELECT * FROM projects WHERE id=?", (p["id"],)).fetchone()
    return {"project": _project_json(ctx.conn, p, ctx.user["id"]), "status": "accepted" if accept else "declined"}


@route("POST", "/api/project-requests/{id}/accept")
def accept_project_request(ctx):
    return _decide_project(ctx, True)


@route("POST", "/api/project-requests/{id}/decline")
def decline_project_request(ctx):
    return _decide_project(ctx, False)


# ======================= people directory =======================
@route("GET", "/api/people")
def list_people(ctx):
    """Public campus directory: name, year, branch, goal, skills and availability. Never email, never grades."""
    out = []
    for r in ctx.conn.execute("SELECT * FROM users ORDER BY id").fetchall():
        p = person(ctx.conn, r)
        sk = skills_of(ctx.conn, r["id"])
        mp = ctx.conn.execute("SELECT * FROM mentor_profiles WHERE user_id=?", (r["id"],)).fetchone()
        item = {**_public(p), "role": r["role"], "rep": r["rep"],
                "skills": {k: v["level"] for k, v in sk.items()}, "status": {k: v["status"] for k, v in sk.items()}}
        if r["role"] == "senior":
            item.update(_mentor_stats(ctx.conn, r["id"], mp))
        out.append(item)
    return {"people": out}


@route("GET", "/api/verify/mine")
def my_verify_requests(ctx):
    """The signed-in user's own pending verification requests (so the Skill Passport can show 'pending')."""
    rows = ctx.conn.execute("SELECT id, skill, note, created_at FROM verify_requests WHERE user_id=? AND status='pending' ORDER BY id",
                            (ctx.user["id"],)).fetchall()
    return {"items": [{"id": r["id"], "skill": r["skill"], "note": r["note"], "created_at": r["created_at"]} for r in rows]}
