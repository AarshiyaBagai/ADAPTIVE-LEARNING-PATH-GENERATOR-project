"""Phase 2b: placement preparation. Answers to quiz questions never leave the server before they are submitted."""
import json

import engine
from db import now_iso
from routes import ApiError, route, need_str, need_int, need_choice, require_role, levels_of
from routes_planner import touch_activity


def _q_public(q: dict) -> dict:
    return {"id": q["id"], "topic": q["topic"], "question": q["q"], "options": q["o"]}


# ======================= adaptive aptitude =======================
def _apt_state(s) -> dict:
    asked = json.loads(s["asked"])
    return {"session_id": s["id"], "number": len(asked), "total": engine.APT_QUESTIONS, "done": bool(s["done"]),
            "question": _q_public(engine.APT[s["current_q"]]) if s["current_q"] else None}


@route("POST", "/api/prep/aptitude/sessions")
def apt_start(ctx):
    """Start a mock. An unfinished earlier mock is discarded, so there is only ever one open session."""
    uid = ctx.user["id"]
    ctx.conn.execute("DELETE FROM aptitude_sessions WHERE user_id=? AND done=0", (uid,))
    first = engine.apt_next([], engine.APT_START_LEVEL)
    cur = ctx.conn.execute("INSERT INTO aptitude_sessions (user_id, level, asked, current_q, created_at) VALUES (?,?,?,?,?)",
                           (uid, engine.APT_START_LEVEL, json.dumps([first]), first, now_iso()))
    s = ctx.conn.execute("SELECT * FROM aptitude_sessions WHERE id=?", (cur.lastrowid,)).fetchone()
    return 201, _apt_state(s)


def _own_session(ctx):
    s = ctx.conn.execute("SELECT * FROM aptitude_sessions WHERE id=?", (int(ctx.params["id"]),)).fetchone()
    if s is None or s["user_id"] != ctx.user["id"]:
        raise ApiError(404, "not_found", "Session not found.")
    return s


@route("GET", "/api/prep/aptitude/sessions/{id}")
def apt_get(ctx):
    return _apt_state(_own_session(ctx))


@route("POST", "/api/prep/aptitude/sessions/{id}/answer")
def apt_answer(ctx):
    s = _own_session(ctx)
    choice = need_int(ctx.body, "choice", 0, 3)
    qid = need_str(ctx.body, "question_id", 1, 10)
    if s["done"] or not s["current_q"]:
        raise ApiError(409, "conflict", "This session is finished.")
    if qid != s["current_q"]:  # the answer must name its question, so a repeated request cannot hit the next one
        raise ApiError(409, "conflict", "That question was already answered.")
    q = engine.APT[s["current_q"]]
    # claim the current question: a double click cannot score the same question twice
    claimed = ctx.conn.execute("UPDATE aptitude_sessions SET current_q=NULL WHERE id=? AND current_q=?", (s["id"], s["current_q"]))
    if claimed.rowcount == 0:
        raise ApiError(409, "conflict", "That question was already answered.")
    ok = choice == q["a"]
    log = json.loads(s["log"]) + [{"id": q["id"], "topic": q["topic"], "lvl": q["lvl"], "ok": ok}]
    level = engine.apt_level_after(s["level"], ok)
    asked = json.loads(s["asked"])
    nxt = engine.apt_next(asked, level)
    if nxt:
        asked.append(nxt)
    ctx.conn.execute("UPDATE aptitude_sessions SET level=?, asked=?, current_q=?, log=?, correct=correct+?, done=? WHERE id=?",
                     (level, json.dumps(asked), nxt, json.dumps(log), int(ok), int(nxt is None), s["id"]))
    out = {"correct": ok, "correct_index": q["a"], "explanation": q["e"]}
    if nxt:
        out["next"] = _apt_state(ctx.conn.execute("SELECT * FROM aptitude_sessions WHERE id=?", (s["id"],)).fetchone())
    else:
        touch_activity(ctx.conn, ctx.user["id"])
        out["summary"] = {"score": s["correct"] + int(ok), "total": len(log), "weak_topics": engine.weak_topics(log)}
    return out


@route("GET", "/api/prep/aptitude/history")
def apt_history(ctx):
    rows = ctx.conn.execute("SELECT id, log, correct, created_at FROM aptitude_sessions WHERE user_id=? AND done=1 "
                            "ORDER BY id DESC LIMIT 20", (ctx.user["id"],)).fetchall()
    hist = []
    for r in rows:
        log = json.loads(r["log"])
        hist.append({"id": r["id"], "date": r["created_at"][:10], "score": r["correct"], "total": len(log),
                     "weak_topics": engine.weak_topics(log)})
    return {"history": hist}


# ======================= technical MCQ =======================
@route("GET", "/api/prep/tech/questions")
def tech_questions(ctx):
    skill = ctx.query.get("skill")
    if skill and skill not in {q["skill"] for q in engine.TECH.values()}:
        raise ApiError(400, "validation", "Unknown topic.")
    done = {r["qid"] for r in ctx.conn.execute("SELECT qid FROM tech_attempts WHERE user_id=?", (ctx.user["id"],)).fetchall()}
    qs = [{**_q_public(q), "skill": q["skill"], "attempted": q["id"] in done}
          for q in engine.TECH.values() if not skill or q["skill"] == skill]
    return {"questions": qs}


@route("POST", "/api/prep/tech/answer")
def tech_answer(ctx):
    """Only the first attempt at a question is counted, so repeating one question cannot farm a verified skill.
    At least 3 counted attempts in a topic at 70% or better marks the skill 'assessed' (level 3 at most).
    Faculty-verified skills are never changed, and levels above 3 are never vouched for by a quiz."""
    qid = need_str(ctx.body, "qid", 1, 10)
    choice = need_int(ctx.body, "choice", 0, 3)
    q = engine.TECH.get(qid)
    if q is None:
        raise ApiError(404, "not_found", "Question not found.")
    uid, c = ctx.user["id"], ctx.conn
    ok = choice == q["a"]
    counted = c.execute("INSERT OR IGNORE INTO tech_attempts (user_id, qid, skill, ok) VALUES (?,?,?,?)",
                        (uid, qid, q["skill"], int(ok))).rowcount == 1
    verified = False
    if counted:
        touch_activity(c, uid)
        n, good = c.execute("SELECT COUNT(*), SUM(ok) FROM tech_attempts WHERE user_id=? AND skill=?", (uid, q["skill"])).fetchone()
        if n >= engine.VERIFY_MIN_ATTEMPTS and good / n >= engine.VERIFY_MIN_ACCURACY:
            cur = c.execute("SELECT level, status FROM user_skills WHERE user_id=? AND skill=?", (uid, q["skill"])).fetchone()
            if cur is None:
                c.execute("INSERT INTO user_skills (user_id, skill, level, status, updated_at) VALUES (?,?,?,?,?)",
                          (uid, q["skill"], engine.VERIFY_LEVEL, "assessed", now_iso()))
                verified = True
            elif cur["status"] != "faculty" and cur["level"] <= engine.VERIFY_LEVEL:
                c.execute("UPDATE user_skills SET level=?, status='assessed', updated_at=? WHERE user_id=? AND skill=?",
                          (max(cur["level"], engine.VERIFY_LEVEL), now_iso(), uid, q["skill"]))
                verified = True
    return {"correct": ok, "correct_index": q["a"], "explanation": q["e"], "counted": counted, "verified": verified}


@route("GET", "/api/prep/tech/stats")
def tech_stats(ctx):
    rows = ctx.conn.execute("SELECT skill, COUNT(*) a, SUM(ok) c FROM tech_attempts WHERE user_id=? GROUP BY skill",
                            (ctx.user["id"],)).fetchall()
    st = {r["skill"]: {"attempts": r["a"], "correct": r["c"], "accuracy": round(r["c"] / r["a"], 3)} for r in rows}
    return {"stats": st, "rule": {"min_attempts": engine.VERIFY_MIN_ATTEMPTS, "min_accuracy": engine.VERIFY_MIN_ACCURACY}}


# ======================= coding list =======================
@route("GET", "/api/prep/coding")
def coding_list(ctx):
    done = {r["cid"] for r in ctx.conn.execute("SELECT cid FROM coding_done WHERE user_id=?", (ctx.user["id"],)).fetchall()}
    items = [{"id": c["id"], "title": c["t"], "difficulty": c["d"], "topic": c["topic"], "done": c["id"] in done}
             for c in engine.CODING.values()]
    return {"problems": items, "solved": len(done), "total": len(items)}


@route("PUT", "/api/prep/coding/{slug}")
def coding_set(ctx):
    cid = ctx.params["slug"]
    if cid not in engine.CODING:
        raise ApiError(404, "not_found", "Problem not found.")
    done = ctx.body.get("done")
    if not isinstance(done, bool):
        raise ApiError(400, "validation", "'done' must be true or false")
    if done:
        ctx.conn.execute("INSERT OR IGNORE INTO coding_done (user_id, cid) VALUES (?,?)", (ctx.user["id"], cid))
        touch_activity(ctx.conn, ctx.user["id"])
    else:
        ctx.conn.execute("DELETE FROM coding_done WHERE user_id=? AND cid=?", (ctx.user["id"], cid))
    return {"id": cid, "done": done}


# ======================= mock interview =======================
@route("GET", "/api/prep/interview/questions")
def interview_questions(ctx):
    cat = need_choice(ctx.query, "category", list(engine.INTERVIEW))
    return {"category": cat, "questions": [{"index": i, "question": q["q"]} for i, q in enumerate(engine.INTERVIEW[cat])]}


@route("POST", "/api/prep/interview/answer")
def interview_answer(ctx):
    cat = need_choice(ctx.body, "category", list(engine.INTERVIEW))
    idx = need_int(ctx.body, "index", 0, 99)
    if idx >= len(engine.INTERVIEW[cat]):
        raise ApiError(404, "not_found", "Question not found.")
    text = need_str(ctx.body, "text", 1, 3000)
    res = engine.score_answer(text, engine.INTERVIEW[cat][idx]["kw"])
    ctx.conn.execute("INSERT INTO interview_answers (user_id, category, qidx, text, score, created_at) VALUES (?,?,?,?,?,?)",
                     (ctx.user["id"], cat, idx, text, res["score"], now_iso()))
    touch_activity(ctx.conn, ctx.user["id"])
    return {**res, "note": "Rule-based practice score (keywords, length, an example or reason). It is not a real interviewer."}


@route("GET", "/api/prep/interview/history")
def interview_history(ctx):
    rows = ctx.conn.execute("SELECT id, category, qidx, score, created_at FROM interview_answers WHERE user_id=? "
                            "ORDER BY id DESC LIMIT 50", (ctx.user["id"],)).fetchall()
    return {"history": [{"id": r["id"], "category": r["category"], "index": r["qidx"], "score": r["score"],
                         "date": r["created_at"][:10]} for r in rows]}


@route("GET", "/api/prep/project-ideas")
def project_ideas(ctx):
    require_role(ctx, "student")
    goal = ctx.user["goal"]
    if goal not in engine.ROLES:
        raise ApiError(409, "no_goal", "Set a target career first.")
    return {"ideas": engine.project_ideas(levels_of(ctx.conn, ctx.user["id"]), goal)}
