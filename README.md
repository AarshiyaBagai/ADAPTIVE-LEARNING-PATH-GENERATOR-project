# ALPG: Adaptive Learning Pathway Generator (frontend only)

A static front end for the ALPG campus platform. There is **no backend**: all data is mock data kept in your browser's `localStorage`. Nothing to install.

## Run it

Double-click `index.html`, or serve the folder:

```
python -m http.server 8000     # then open http://localhost:8000
```

Use **Reset demo data** in the sidebar to start over.

## Demo roles (sidebar dropdown)

| Role | What to try |
|------|-------------|
| Student (Aarav) | Dashboard, pathway, resources, Q&A, mentor requests, team matching, readiness, aptitude, technical, mock interview |
| Senior mentor (Priya) | Accept/decline mentor requests, see how your shared resources perform |
| Faculty (Dr. Mehta) | Cohort dashboard, verify skills, verify Q&A answers |

**End-to-end demo:** Student → Mentorship → request a session from Priya → switch to Senior and accept → back to Student and log pre/post scores → improvement shows up.

## Features

Dashboard · Skill Passport (self-reported / assessment-verified / faculty-verified) · Adaptive pathway (prerequisite-ordered skill gaps) · Resource Hub with effectiveness and synonym search · Q&A forum (votes, accepted, faculty-verified, similar-question hints) · Senior–junior mentorship with match score · Project & team matcher (weighted score + balanced team) · Project generator · Internship readiness (role or pasted job description) · Adaptive aptitude mock · Technical MCQ + coding list · Mock interview · Study planner & groups · Faculty dashboard.

## How the "AI" works (all in `logic.js`, all explainable)

- **Skill gap:** `max(0, required − current)`; unmet prerequisites are added and topologically ordered.
- **Mentor match:** 0.5·skill coverage of your gaps + 0.25·shared free slots + 0.25·goal/interest fit.
- **Team match:** 0.45·skills + 0.20·experience + 0.20·availability + 0.15·interest, then a greedy pick that covers missing skills. Weights are starting values, not tuned.
- **Aptitude:** difficulty steps up after a correct answer and down after a wrong one.
- **Mock interview:** rule-based rubric (keyword coverage, length, examples). It is a practice aid, **not** a real AI judge.
- **Search:** keyword match with a small synonym table (no embeddings).

## Limits of this front end

No real login, file uploads, code execution, or LMS sync; the data is sample data (the faculty cohort numbers are illustrative). To go further, add a backend (e.g. FastAPI + PostgreSQL) and replace the functions in `logic.js` with API calls.

## Files

`index.html` shell · `styles.css` · `data.js` mock data · `logic.js` algorithms and state · `pages.js` page templates · `app.js` router and events
