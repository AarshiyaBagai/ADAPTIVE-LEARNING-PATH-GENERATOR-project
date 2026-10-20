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
