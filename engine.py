"""ALPG recommendation engine: pure functions, no I/O.

Mirrors the logic in frontend/logic.js so both sides give the same answers.
Everything here is explainable rule-based scoring, not a trained model.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "taxonomy.json"), encoding="utf-8") as _f:
    TAXONOMY = json.load(_f)

SKILLS = TAXONOMY["skills"]   # key -> {name, pre, kw}
ROLES = TAXONOMY["roles"]     # name -> {desc, req}
DAYS = TAXONOMY["days"]

SYNONYMS = {
    "noise": ["median", "filter", "denoising", "denoise"], "denoise": ["median", "filter", "noise"],
    "tree": ["trees", "binary", "bst"], "trees": ["tree", "binary"], "join": ["joins"], "joins": ["join"],
    "ml": ["machine", "learning", "scikit", "model"], "machine": ["ml", "scikit"],
    "interview": ["communication", "hr"], "probability": ["dice", "conditional", "stats"],
    "dice": ["probability"], "thread": ["process", "threads"], "process": ["thread", "scheduling"],
}


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


# ---------- gaps, pathway, readiness ----------
def gap_list(levels: dict, role: str) -> list:
    """gap = max(0, required - current) for every skill the role requires."""
    req = ROLES[role]["req"]
    out = []
    for k, r in req.items():
        c = levels.get(k, 0)
        out.append({"skill": k, "required": r, "current": c, "gap": max(0, r - c)})
    return out


def pathway(levels: dict, role: str) -> list:
    """Prerequisite-aware learning order (topological sort of the skill graph).

    Unmet prerequisites (level < 2) are added automatically and ordered first.
    A step is 'locked' while one of its prerequisites is itself still to be learned,
    the first unlocked step is 'current', the rest are 'next'.
    """
    req = ROLES[role]["req"]

    def lvl(k):
        return levels.get(k, 0)

    needed = {}  # insertion-ordered

    def add(k, target, why):
        if k in needed:
            needed[k]["target"] = max(needed[k]["target"], target)
            return
        needed[k] = {"skill": k, "target": target, "why": why}
        for pk in SKILLS[k]["pre"]:
            if lvl(pk) < 2:
                add(pk, 2, "prerequisite")

    for k, r in req.items():
        if lvl(k) < r:
            add(k, r, f"required for {role}")

    order, seen = [], set()

    def visit(k):
        if k in seen or k not in needed:
            return
        seen.add(k)
        for pk in SKILLS[k]["pre"]:
            visit(pk)
        order.append(k)

    for k in list(needed):
        visit(k)

    steps, current_set = [], False
    for k in order:
        n = needed[k]
        blocked = any(pk in needed for pk in SKILLS[k]["pre"])
        if blocked:
            state = "locked"
        elif not current_set:
            state, current_set = "current", True
        else:
            state = "next"
        steps.append({"skill": k, "name": SKILLS[k]["name"], "from": lvl(k), "target": n["target"],
                      "why": n["why"], "state": state})
    return steps


def readiness(levels: dict, req: dict) -> dict:
    """Share of required skill levels already demonstrated, plus a per-skill breakdown."""
    got = tot = 0
    rows = []
    for k, r in req.items():
        c = levels.get(k, 0)
        got += min(c, r)
        tot += r
        state = "ok" if c >= r else ("partial" if c > 0 else "missing")
        rows.append({"skill": k, "name": SKILLS[k]["name"], "required": r, "current": c, "state": state})
    pct = _round_half_up(100 * got / tot) if tot else 0
    return {"pct": pct, "rows": rows}


def extract_skills(text: str) -> dict:
    """Keyword-based skill extraction from a job description (required level assumed 3)."""
    t = text.lower()
    t = re.sub(r"[^a-z0-9+#.\- ]", " ", t)
    t = re.sub(r"[.\-]+(?=\s|$)", " ", t)
    t = " " + re.sub(r"\s+", " ", t) + " "
    return {k: 3 for k, s in SKILLS.items() if any(f" {w} " in t for w in s["kw"])}


# ---------- search ----------
def tokens(s: str) -> list:
    return [w for w in re.split(r"[^a-z0-9+#]+", str(s).lower()) if w]


# Everyday words that say nothing about a topic. Without this, "remove noise from image" would
# match any title containing "from", which makes results look random.
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it my of on or so the to we what when "
    "where which who why with you your".split())


def search_score(query: str, text: str) -> int:
    """Keyword match: exact word = 2, prefix = 1, synonym hit = 1. Stopwords are ignored."""
    t = tokens(text)
    score = 0
    for w in tokens(query):
        if w in STOPWORDS:
            continue
        if w in t:
            score += 2
        elif len(w) > 2 and any(x.startswith(w) for x in t):
            score += 1
        for s in SYNONYMS.get(w, []):
            if s in t:
                score += 1
    return score


# ---------- resources ----------
def gap_relevance(levels: dict, role: str) -> dict:
    """skill -> 0..1 relevance, based on how large the learner's gap is for that skill."""
    return {g["skill"]: min(1.0, g["gap"] / 3) for g in gap_list(levels, role) if g["gap"] > 0}


def resource_rank_score(relevance: float, gain: float) -> float:
    return 0.7 * relevance + 0.3 * min(1.0, (gain or 0) / 4)


# ======================= content banks (quizzes, interview, project ideas) =======================
with open(os.path.join(_HERE, "content.json"), encoding="utf-8") as _f:
    CONTENT = json.load(_f)

APT = {q["id"]: q for q in CONTENT["APT"]}
TECH = {q["id"]: q for q in CONTENT["TECH"]}
INTERVIEW = CONTENT["INTERVIEW"]
PROJECT_IDEAS = CONTENT["PROJECT_IDEAS"]
GROUPS = CONTENT["GROUPS"]
CODING = {c["id"]: c for c in CONTENT["CODING"]}

APT_START_LEVEL = 2
APT_QUESTIONS = 8
VERIFY_MIN_ATTEMPTS = 3
VERIFY_MIN_ACCURACY = 0.7
VERIFY_LEVEL = 3          # a quiz can vouch for level 3 at most
MIN_GROUP_SIZE = 5        # faculty analytics hide any group smaller than this


def mentor_match(mentor: dict, student: dict) -> dict:
    """score = 0.5*K (gaps the mentor covers) + 0.25*A (shared free slots) + 0.25*I (goal and interest fit)."""
    gs = [g for g in gap_list(student["skills"], student["goal"]) if g["gap"] > 0]
    tot = sum(g["gap"] for g in gs) or 1
    K, why = 0.0, []
    for g in gs:
        ml = mentor["skills"].get(g["skill"], 0)
        if ml >= g["required"]:
            K += g["gap"]
            why.append(SKILLS[g["skill"]]["name"])
        elif ml > g["current"]:
            K += g["gap"] * 0.5
    K /= tot
    overlap = [d for d in mentor["avail"] if d in student["avail"]]
    A = min(1.0, len(overlap) / 2)
    shared = [i for i in mentor["interests"] if i in student["interests"]]
    I = (0.6 if mentor["goal"] == student["goal"] else 0.0) + min(0.4, 0.2 * len(shared))
    return {"score": round(0.5 * K + 0.25 * A + 0.25 * I, 4), "skills": round(K, 3), "availability": round(A, 3),
            "fit": round(I, 3), "overlap": overlap, "covers": why}


def team_score(cand: dict, proj: dict, owner_avail: list) -> dict:
    """S = 0.45*K + 0.20*E + 0.20*A + 0.15*I (K skill fit, E experience, A shared slots, I interest)."""
    needs = proj["needs"]
    K = sum(min(1.0, cand["skills"].get(k, 0) / 4) for k in needs) / len(needs)
    E = min(1.0, (cand.get("projects") or 0) / 4)
    A = min(1.0, len([d for d in cand["avail"] if d in owner_avail]) / 2)
    tags = proj["tags"]
    I = min(1.0, len([i for i in cand["interests"] if i in tags]) / max(1, min(2, len(tags)))) if tags else 0.0
    return {"score": round(0.45 * K + 0.2 * E + 0.2 * A + 0.15 * I, 4), "skills": round(K, 3),
            "experience": round(E, 3), "availability": round(A, 3), "interest": round(I, 3)}


def rank_candidates(cands: list, proj: dict, owner_avail: list) -> list:
    out = [dict(c, **{"match": team_score(c, proj, owner_avail)}) for c in cands]
    return sorted(out, key=lambda x: (-x["match"]["score"], x["id"]))


def suggest_team(ranked: list, proj: dict, member_skills: list) -> dict:
    """Greedy pick: each seat goes to the candidate with the best score plus 0.25 per newly covered skill."""
    needs = proj["needs"]
    covered = {k for k in needs if any(ms.get(k, 0) >= 3 for ms in member_skills)}
    pool, team = list(ranked), []
    free = proj["size"] - len(member_skills)
    while len(team) < free and pool:
        best, bv = None, -1.0
        for x in pool:
            gain = sum(1 for k in needs if k not in covered and x["skills"].get(k, 0) >= 3)
            v = x["match"]["score"] + 0.25 * gain
            if v > bv:
                best, bv = x, v
        team.append(best)
        pool.remove(best)
        covered |= {k for k in needs if best["skills"].get(k, 0) >= 3}
    return {"team": team, "covered": sorted(covered), "missing": [k for k in needs if k not in covered]}


def project_ideas(levels: dict, role: str) -> list:
    gaps = {g["skill"] for g in gap_list(levels, role) if g["gap"] > 0}
    out = []
    for idea in PROJECT_IDEAS:
        ks = list(idea["skills"])
        stretch = [k for k in ks if levels.get(k, 0) < idea["skills"][k]]
        jump = max(idea["skills"][k] - levels.get(k, 0) for k in ks)
        builds = [k for k in ks if k in gaps]
        score = len(builds) * 2 - max(0, jump - 1) * 2 + (0.5 if jump <= 0 else 0)
        out.append({**idea, "stretch": stretch, "builds": builds, "max_jump": jump, "fits": jump <= 1, "score": score})
    return sorted(out, key=lambda x: -x["score"])


def apt_next(asked: list, level: int, limit: int = APT_QUESTIONS):
    """Next question id: the unasked one whose difficulty is closest to the current level. None when finished."""
    pool = [q for qid, q in APT.items() if qid not in asked]
    if not pool or len(asked) >= limit:
        return None
    pool.sort(key=lambda q: abs(q["lvl"] - level))  # stable sort: bank order breaks ties
    return pool[0]["id"]


def apt_level_after(level: int, correct: bool) -> int:
    return max(1, min(3, level + (1 if correct else -1)))


def weak_topics(log: list) -> list:
    t = {}
    for l in log:
        v = t.setdefault(l["topic"], {"a": 0, "c": 0})
        v["a"] += 1
        v["c"] += 1 if l["ok"] else 0
    rows = [{"topic": k, "accuracy": round(v["c"] / v["a"], 3), "asked": v["a"]} for k, v in t.items()]
    return sorted(rows, key=lambda r: (r["accuracy"], r["topic"]))


CLARITY_RE = re.compile(r"(for example|for instance|e\.g\.|because|so that|which means|\d)")


def score_answer(text: str, kw: list) -> dict:
    """0.5*keyword coverage + 0.3*length (45 words = full) + 0.2*clarity (an example or a reason). Rule-based."""
    words = text.split()
    t = text.lower()
    hit = [k for k in kw if k in t]
    missed = [k for k in kw if k not in t]
    cov = min(1.0, len(hit) / max(3, -(-len(kw) // 2)))
    ln = min(1.0, len(words) / 45)
    clar = 1.0 if CLARITY_RE.search(t) else 0.3
    return {"score": _round_half_up((0.5 * cov + 0.3 * ln + 0.2 * clar) * 100), "hit": hit, "missed": missed,
            "words": len(words), "coverage": round(cov, 3), "length": round(ln, 3), "clarity": clar}


def streak_from_days(days: list, today: str) -> int:
    """Consecutive active days ending today (or yesterday, so the streak is not lost before you study today)."""
    from datetime import date, timedelta
    have = set(days)
    d = date.fromisoformat(today)
    if d.isoformat() not in have:
        d -= timedelta(days=1)
    n = 0
    while d.isoformat() in have:
        n += 1
        d -= timedelta(days=1)
    return n
