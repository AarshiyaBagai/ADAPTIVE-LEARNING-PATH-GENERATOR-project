"""Phase 2c: planner (tasks, weekly plan, study groups), grades, activity streak, dashboards, faculty analytics."""
import json
from datetime import datetime, timezone

import engine
from db import now_iso
from routes import ApiError, route, need_str, need_int, require_role, levels_of


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def touch_activity(conn, user_id) -> None:
    """Record that the user did something useful today (feeds the streak)."""
    conn.execute("INSERT OR IGNORE INTO activity (user_id, day) VALUES (?,?)", (user_id, today()))


def streak_of(conn, user_id) -> dict:
    days = [r["day"] for r in conn.execute(
        "SELECT day FROM activity WHERE user_id=? ORDER BY day DESC LIMIT 400", (user_id,)).fetchall()]
    return {"days": engine.streak_from_days(days, today()), "last_active": days[0] if days else None,
            "active_today": bool(days) and days[0] == today()}


@route("GET", "/api/activity")
def get_activity(ctx):
    rows = ctx.conn.execute("SELECT day FROM activity WHERE user_id=? ORDER BY day DESC LIMIT 30", (ctx.user["id"],)).fetchall()
    return {"streak": streak_of(ctx.conn, ctx.user["id"]), "recent_days": [r["day"] for r in rows]}


@route("POST", "/api/activity")
def post_activity(ctx):
    """Mark today as an active day (the app calls this after a study action it handled locally)."""
    touch_activity(ctx.conn, ctx.user["id"])
    return {"streak": streak_of(ctx.conn, ctx.user["id"])}


# ======================= tasks =======================
def _task(r):
    return {"id": r["id"], "text": r["text"], "done": bool(r["done"]), "created_at": r["created_at"]}


def _own_task(ctx):
    r = ctx.conn.execute("SELECT * FROM tasks WHERE id=?", (int(ctx.params["id"]),)).fetchone()
    # someone else's task looks exactly like a missing one
    if r is None or r["user_id"] != ctx.user["id"]:
        raise ApiError(404, "not_found", "Task not found.")
    return r


@route("GET", "/api/tasks")
def list_tasks(ctx):
    rows = ctx.conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 200", (ctx.user["id"],)).fetchall()
    return {"tasks": [_task(r) for r in rows]}


@route("POST", "/api/tasks")
def create_task(ctx):
    text = need_str(ctx.body, "text", 1, 100)
    if ctx.conn.execute("SELECT COUNT(*) FROM tasks WHERE user_id=?", (ctx.user["id"],)).fetchone()[0] >= 200:
        raise ApiError(409, "limit", "You have too many tasks. Delete some first.")
    cur = ctx.conn.execute("INSERT INTO tasks (user_id, text, created_at) VALUES (?,?,?)", (ctx.user["id"], text, now_iso()))
    return 201, {"task": _task(ctx.conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone())}


@route("PUT", "/api/tasks/{id}")
def update_task(ctx):
    t = _own_task(ctx)
    text = need_str(ctx.body, "text", 1, 100, required=False)
    done = ctx.body.get("done")
    if done is not None and not isinstance(done, bool):
        raise ApiError(400, "validation", "'done' must be true or false")
    ctx.conn.execute("UPDATE tasks SET text=?, done=? WHERE id=?",
                     (text if text is not None else t["text"], int(done) if done is not None else t["done"], t["id"]))
    if done and not t["done"]:
        touch_activity(ctx.conn, ctx.user["id"])
    return {"task": _task(ctx.conn.execute("SELECT * FROM tasks WHERE id=?", (t["id"],)).fetchone())}


@route("DELETE", "/api/tasks/{id}")
def delete_task(ctx):
    t = _own_task(ctx)
    ctx.conn.execute("DELETE FROM tasks WHERE id=?", (t["id"],))
    return {"deleted": t["id"]}


# ======================= weekly plan =======================
@route("GET", "/api/plan/week")
def week_plan(ctx):
    """Free slots paired with the open (not locked) pathway steps, in rotation."""
    u = ctx.user
    if not u["goal"] or u["goal"] not in engine.ROLES:
        raise ApiError(409, "no_goal", "Set a target career first.")
    steps = [s for s in engine.pathway(levels_of(ctx.conn, u["id"]), u["goal"]) if s["state"] != "locked"]
    avail = json.loads(u["avail"])
    plan = [{"slot": d, "skill": steps[i % len(steps)]["skill"] if steps else None,
             "title": (steps[i % len(steps)]["name"] + " practice") if steps else "Free revision"}
            for i, d in enumerate(avail)]
    return {"goal": u["goal"], "plan": plan}


# ======================= study groups =======================
def _group(conn, g, uid):
    joined = conn.execute("SELECT 1 FROM group_members WHERE group_id=? AND user_id=?", (g["id"], uid)).fetchone() is not None
    n = conn.execute("SELECT COUNT(*) FROM group_members WHERE group_id=?", (g["id"],)).fetchone()[0]
    return {"id": g["id"], "name": g["name"], "goal": g["goal"], "skill": g["skill"],
            "members": g["base_members"] + n, "joined": joined}


@route("GET", "/api/groups")
def list_groups(ctx):
    rows = ctx.conn.execute("SELECT * FROM study_groups ORDER BY id").fetchall()
    return {"groups": [_group(ctx.conn, g, ctx.user["id"]) for g in rows]}


def _group_or_404(ctx):
    g = ctx.conn.execute("SELECT * FROM study_groups WHERE id=?", (ctx.params["slug"],)).fetchone()
    if g is None:
        raise ApiError(404, "not_found", "Group not found.")
    return g


@route("POST", "/api/groups/{slug}/join")
def join_group(ctx):
    g = _group_or_404(ctx)
    ctx.conn.execute("INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)", (g["id"], ctx.user["id"]))
    return {"group": _group(ctx.conn, g, ctx.user["id"])}


@route("DELETE", "/api/groups/{slug}/join")
def leave_group(ctx):
    g = _group_or_404(ctx)
    ctx.conn.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (g["id"], ctx.user["id"]))
    return {"group": _group(ctx.conn, g, ctx.user["id"])}


# ======================= grades (private to each student) =======================
@route("GET", "/api/grades")
def list_grades(ctx):
    rows = ctx.conn.execute("SELECT subject, score FROM grades WHERE user_id=? ORDER BY subject", (ctx.user["id"],)).fetchall()
    return {"grades": [{"subject": r["subject"], "score": r["score"]} for r in rows]}


@route("PUT", "/api/grades")
def put_grade(ctx):
    require_role(ctx, "student")
    subject = need_str(ctx.body, "subject", 2, 60)
    score = need_int(ctx.body, "score", 0, 100)
    ctx.conn.execute("INSERT INTO grades (user_id, subject, score) VALUES (?,?,?)"
                     " ON CONFLICT(user_id, subject) DO UPDATE SET score=excluded.score", (ctx.user["id"], subject, score))
    return {"grade": {"subject": subject, "score": score}}


@route("DELETE", "/api/grades")
def delete_grade(ctx):
    subject = ctx.query.get("subject", "").strip()
    if not subject:
        raise ApiError(400, "validation", "'subject' is required")
    cur = ctx.conn.execute("DELETE FROM grades WHERE user_id=? AND subject=?", (ctx.user["id"], subject))
    if cur.rowcount == 0:
        raise ApiError(404, "not_found", "Grade not found.")
    return {"deleted": subject}


# ======================= dashboards =======================
def student_alerts(conn, u) -> list:
    out = []
    levels = levels_of(conn, u["id"])
    if u["goal"] in engine.ROLES:
        gs = sorted([g for g in engine.gap_list(levels, u["goal"]) if g["gap"] > 0], key=lambda g: -g["gap"])
        if gs:
            g = gs[0]
            out.append({"type": "warn", "message": f"Biggest gap for {u['goal']}: {engine.SKILLS[g['skill']]['name']} "
                        f"(you are at level {g['current']}, the role needs {g['required']})."})
    for r in conn.execute("SELECT subject, score FROM grades WHERE user_id=? AND score<65 ORDER BY score", (u["id"],)).fetchall():
        out.append({"type": "bad", "message": f"{r['subject']} is at {r['score']}%. Suggested rescue plan: one practice "
                    "set plus a mentor session this week."})
    n = conn.execute("SELECT COUNT(*) FROM questions q WHERE q.user_id=? AND NOT EXISTS "
                     "(SELECT 1 FROM answers a WHERE a.question_id=q.id)", (u["id"],)).fetchone()[0]
    if n:
        out.append({"type": "ok", "message": f"{n} of your questions are still waiting for an answer."})
    n = conn.execute("SELECT COUNT(*) FROM mentor_requests WHERE student_id=? AND status='accepted' AND pre IS NULL",
                     (u["id"],)).fetchone()[0]
    if n:
        out.append({"type": "", "message": f"{n} accepted mentor session(s): log your before/after scores to measure improvement."})
    return out


@route("GET", "/api/dashboard")
def dashboard(ctx):
    u, c = ctx.user, ctx.conn
    one = lambda sql, *a: c.execute(sql, a).fetchone()[0]
    if u["role"] == "student":
        levels = levels_of(c, u["id"])
        body = {"role": "student", "streak": streak_of(c, u["id"]), "alerts": student_alerts(c, u)}
        if u["goal"] in engine.ROLES:
            body["goal"] = u["goal"]
            body["readiness"] = engine.readiness(levels, engine.ROLES[u["goal"]]["req"])["pct"]
            steps = engine.pathway(levels, u["goal"])
            body["next_step"] = next((s for s in steps if s["state"] == "current"), None)
            body["steps_remaining"] = len(steps)
        body["counts"] = {
            "open_tasks": one("SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=0", u["id"]),
            "bookmarks": one("SELECT COUNT(*) FROM bookmarks WHERE user_id=?", u["id"]),
            "pending_mentor_requests": one("SELECT COUNT(*) FROM mentor_requests WHERE student_id=? AND status='pending'", u["id"]),
            "project_invitations": one("SELECT COUNT(*) FROM project_requests WHERE user_id=? AND kind='invite' AND status='pending'", u["id"]),
            "coding_solved": one("SELECT COUNT(*) FROM coding_done WHERE user_id=?", u["id"]),
        }
        last = c.execute("SELECT log, correct FROM aptitude_sessions WHERE user_id=? AND done=1 ORDER BY id DESC LIMIT 1",
                         (u["id"],)).fetchone()
        body["last_aptitude"] = {"score": last["correct"], "total": len(json.loads(last["log"]))} if last else None
        return body
    if u["role"] == "senior":
        gain = c.execute("SELECT AVG(post-pre) FROM mentor_requests WHERE mentor_id=? AND pre IS NOT NULL", (u["id"],)).fetchone()[0]
        mp = c.execute("SELECT * FROM mentor_profiles WHERE user_id=?", (u["id"],)).fetchone()
        acc = one("SELECT COUNT(*) FROM mentor_requests WHERE mentor_id=? AND status='accepted'", u["id"])
        return {"role": "senior", "rep": u["rep"],
                "pending_requests": one("SELECT COUNT(*) FROM mentor_requests WHERE mentor_id=? AND status='pending'", u["id"]),
                "mentees": (mp["base_mentees"] if mp else 0) + acc, "avg_gain": round(gain, 2) if gain is not None else None,
                "verified_skills": one("SELECT COUNT(*) FROM user_skills WHERE user_id=? AND status!='self'", u["id"]),
                "unanswered_questions": one("SELECT COUNT(*) FROM questions q WHERE NOT EXISTS "
                                            "(SELECT 1 FROM answers a WHERE a.question_id=q.id)")}
    return {"role": "faculty", "pending_verifications": one("SELECT COUNT(*) FROM verify_requests WHERE status='pending'")}


# ======================= faculty analytics (aggregates only) =======================
@route("GET", "/api/faculty/analytics", "faculty")
def faculty_analytics(ctx):
    """Cohort figures with no names and no emails. Any group smaller than MIN_GROUP_SIZE is withheld, so a
    figure can never single out one student."""
    c, k = ctx.conn, engine.MIN_GROUP_SIZE
    students = c.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    suppressed = 0

    struggle = []
    for r in c.execute("SELECT subject, COUNT(*) n, AVG(score) avg, SUM(score<65) low FROM grades g "
                       "JOIN users u ON u.id=g.user_id AND u.role='student' GROUP BY subject").fetchall():
        if r["n"] < k:
            suppressed += 1
            continue
        struggle.append({"subject": r["subject"], "students": r["n"], "average": round(r["avg"], 1),
                         "share_below_65": round(100 * r["low"] / r["n"])})
    struggle.sort(key=lambda x: (-x["share_below_65"], x["subject"]))

    per = c.execute("SELECT AVG(score) a FROM grades g JOIN users u ON u.id=g.user_id AND u.role='student' GROUP BY g.user_id").fetchall()
    at_risk = None
    if len(per) >= k:
        at_risk = {"high": sum(1 for r in per if r["a"] < 55), "medium": sum(1 for r in per if 55 <= r["a"] < 65),
                   "students_with_grades": len(per)}
    elif per:
        suppressed += 1

    skills = []
    for r in c.execute("SELECT skill, COUNT(*) n, AVG(level) avg, SUM(status!='self') ver FROM user_skills s "
                       "JOIN users u ON u.id=s.user_id AND u.role='student' GROUP BY skill").fetchall():
        if r["n"] < k:
            suppressed += 1
            continue
        skills.append({"skill": r["skill"], "name": engine.SKILLS[r["skill"]]["name"], "students": r["n"],
                       "average_level": round(r["avg"], 2), "verified_share": round(100 * r["ver"] / r["n"])})
    skills.sort(key=lambda x: x["average_level"])

    readiness, by_goal = [], {}
    for u in c.execute("SELECT id, goal FROM users WHERE role='student' AND goal IS NOT NULL").fetchall():
        if u["goal"] in engine.ROLES:
            by_goal.setdefault(u["goal"], []).append(engine.readiness(levels_of(c, u["id"]), engine.ROLES[u["goal"]]["req"])["pct"])
    for goal, vals in by_goal.items():
        if len(vals) < k:
            suppressed += 1
            continue
        readiness.append({"goal": goal, "students": len(vals), "average_readiness": round(sum(vals) / len(vals))})

    return {"students": students, "min_group_size": k, "withheld_groups": suppressed, "struggle": struggle,
            "at_risk": at_risk, "skills": skills, "readiness_by_goal": readiness,
            "pending_verifications": c.execute("SELECT COUNT(*) FROM verify_requests WHERE status='pending'").fetchone()[0],
            "mentoring": {"accepted_sessions": c.execute("SELECT COUNT(*) FROM mentor_requests WHERE status='accepted'").fetchone()[0],
                          "measured_sessions": c.execute("SELECT COUNT(*) FROM mentor_requests WHERE pre IS NOT NULL").fetchone()[0]}}
