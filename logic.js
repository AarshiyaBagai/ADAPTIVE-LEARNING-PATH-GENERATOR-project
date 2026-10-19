/* ALPG client-side logic: state, matching, pathway, quizzes, charts. No backend. */

const $ = (s, r) => (r || document).querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clone = o => JSON.parse(JSON.stringify(o));
const uid = p => p + Math.random().toString(36).slice(2, 8);

/* ---------- State ---------- */
const KEY = 'alpg_frontend_v1';
function loadState() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) { const j = JSON.parse(raw); if (j && j.version === SEED.version) return j; }
  } catch (e) { /* ignore */ }
  return clone(SEED);
}
let S = loadState();
function personalDefaults() {
  return { bookmarks: [], ratings: {}, quiz: { history: [] }, tech: { stats: {} }, interviews: [], tasks: [], groups: [], streak: { days: 0, last: '' }, coding: [] };
}
function stashPersonal() {
  if (!S.session) return;
  S.users = S.users || {};
  const o = {}; PERSONAL.forEach(k => { o[k] = S[k]; });
  S.users[S.session.uid] = clone(o);
}
function loadPersonal(id) {
  const o = clone((S.users && S.users[id]) || personalDefaults());
  PERSONAL.forEach(k => { S[k] = o[k]; });
}
function save() { try { stashPersonal(); localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* ignore */ } }
function resetState() { S = clone(SEED); save(); }

/* ---------- Demo authentication (client-side only: NOT secure) ---------- */
function attemptLogin(email, pw) {
  const a = S.accounts.find(x => x.email === String(email).trim().toLowerCase());
  return a && !String(a.pw).startsWith('!') && a.pw === pw ? a.uid : null;
}
function login(id) {
  const p = person(id);
  S.session = { uid: id }; S.meId = id; S.role = p.role;
  loadPersonal(id); save();
}
function logout() { save(); S.session = null; S.token = null; save(); }
function registerUser(o) {
  const name = String(o.name).trim(), email = String(o.email).trim().toLowerCase();
  if (name.length < 2) return { err: 'Please enter your full name.' };
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { err: 'Enter a valid email address.' };
  if (String(o.pw).length < 8) return { err: 'Password must be at least 8 characters.' };
  if (o.pw !== o.pw2) return { err: 'Passwords do not match.' };
  if (S.accounts.some(a => a.email === email)) return { err: 'An account with this email already exists.' };
  const id = uid('u');
  S.people.push({ id, name, role: 'student', year: Number(o.year) || 3, branch: o.branch || 'CSE', goal: ROLES[o.goal] ? o.goal : 'ML Engineer', cgpa: null,
    skills: {}, status: {}, interests: o.interests || [], avail: o.avail && o.avail.length ? o.avail : ['Mon eve', 'Wed eve'], projects: 0, rep: 0, learn: { style: 'Visual' }, grades: [] });
  S.accounts.push({ email, pw: o.pw, uid: id });
  save();
  return { uid: id };
}

const person = id => S.people.find(p => p.id === id);
const me = () => person(S.meId);
const ROLE_USER = { student: 'u1', senior: 'u2', faculty: 'f1' };
const SHORT = { python: 'Python', dsa: 'DSA', oop: 'OOP', sql: 'SQL', dbms: 'DBMS', os: 'OS', net: 'Networks', git: 'Git', web: 'Web', react: 'React', stats: 'Stats', ml: 'ML', comm: 'Comm.' };
const COLORS = ['#4f46e5', '#7c3aed', '#0891b2', '#16a34a', '#d97706', '#db2777', '#2563eb'];
const STATUS = {
  self: { t: 'Self-reported', c: 'grey' },
  assessed: { t: 'Assessment-verified', c: '' },
  faculty: { t: 'Faculty-verified', c: 'ok' },
};

function initials(n) { return n.split(' ').filter(w => !w.endsWith('.')).map(w => w[0]).slice(0, 2).join('').toUpperCase(); }
function avatar(p, cls) {
  const c = COLORS[p.id.charCodeAt(p.id.length - 1) % COLORS.length];
  return `<span class="avatar ${cls || ''}" style="background:${c}" aria-hidden="true">${esc(initials(p.name))}</span>`;
}

/* ---------- Streak ---------- */
function dayStr(d) { return d.toISOString().slice(0, 10); }
function touchStreak() {
  const today = dayStr(new Date());
  const y = dayStr(new Date(Date.now() - 864e5));
  if (S.streak.last === today) return;
  if (S.streak.last === '' || S.streak.last === y) S.streak.days += 1; else S.streak.days = 1;
  S.streak.last = today;
}

/* ---------- Server bridge (used only when a backend answers) ---------- */
function adoptServerUser(u, token, skills) {
  const email = String(u.email).toLowerCase();
  let acct = S.accounts.find(a => a.email === email);
  let p = acct && person(acct.uid);
  if (!p) {
    const id = uid('u');
    p = { id, name: u.name, role: u.role, year: u.year, branch: u.branch, goal: u.goal, cgpa: null, skills: {}, status: {},
      interests: [], avail: [], projects: 0, rep: 0, learn: { style: 'Visual' }, grades: [] };
    S.people.push(p);
    S.accounts.push({ email, pw: '!server', uid: id }); // local password disabled: sign-in goes through the server
  }
  Object.assign(p, { name: u.name, year: u.year, branch: u.branch, goal: u.goal || p.goal, rep: u.rep, interests: u.interests || [], avail: u.avail || [] });
  if (skills) {
    p.skills = {}; p.status = {};
    Object.entries(skills).forEach(([k, v]) => { p.skills[k] = v.level; p.status[k] = v.status; });
  }
  login(p.id);
  S.token = token;
  save();
  return p;
}

async function serverLogin(email, pw) {
  const r = await API.call('POST', '/api/auth/login', { email: String(email).trim(), password: pw });
  if (r.status === 0) { API.online = false; return { offline: true }; }
  if (!r.ok) return { err: r.message || 'Sign-in failed.' };
  const me = await API.call('GET', '/api/auth/me', null, r.data.token);
  const p = adoptServerUser(r.data.user, r.data.token, me.ok ? me.data.skills : null);
  return { ok: true, id: p.id };
}

async function serverRegister(o) {
  const r = await API.call('POST', '/api/auth/register', { name: o.name, email: o.email, password: o.pw, year: Number(o.year) || 3, branch: o.branch, goal: o.goal });
  if (r.status === 0) { API.online = false; return { offline: true }; }
  if (!r.ok) return { err: r.message || 'Could not create the account.' };
  const p = adoptServerUser(r.data.user, r.data.token, {});
  return { ok: true, id: p.id };
}

/* Best-effort write-through of changes the server already understands. Failures never block the UI. */
async function pushToServer(method, path, body) {
  if (!API.online || !S.token) return null;
  const r = await API.call(method, path, body, S.token);
  if (r.status === 401) { logout(); AUTH.err = 'Your session expired. Please sign in again.'; return r; }
  return r;
}

/* ---------- Skill gaps and pathway ---------- */
function gapList(p, role) {
  const req = (ROLES[role] || ROLES['ML Engineer']).req;
  return Object.entries(req).map(([k, r]) => {
    const c = p.skills[k] || 0;
    return { k, r, c, g: Math.max(0, r - c) };
  });
}

function pathway(p, role) {
  const req = (ROLES[role] || ROLES['ML Engineer']).req;
  const lvl = k => p.skills[k] || 0;
  const needed = new Map();
  const add = (k, target, why) => {
    if (needed.has(k)) { needed.get(k).target = Math.max(needed.get(k).target, target); return; }
    needed.set(k, { k, target, why });
    SKILLS[k].pre.forEach(pk => { if (lvl(pk) < 2) add(pk, 2, 'prerequisite'); });
  };
  Object.entries(req).forEach(([k, r]) => { if (lvl(k) < r) add(k, r, 'required for ' + role); });
  const order = [], seen = new Set();
  const visit = k => {
    if (seen.has(k) || !needed.has(k)) return;
    seen.add(k);
    SKILLS[k].pre.forEach(visit);
    order.push(k);
  };
  [...needed.keys()].forEach(visit);
  let currentSet = false;
  return order.map(k => {
    const n = needed.get(k);
    const blocked = SKILLS[k].pre.some(pk => needed.has(pk));
    let state = 'next';
    if (blocked) state = 'locked';
    else if (!currentSet) { state = 'current'; currentSet = true; }
    return { k, from: lvl(k), target: n.target, why: n.why, state };
  });
}

function completeStep(k) {
  const p = me();
  const cur = p.skills[k] || 0;
  p.skills[k] = Math.min(5, cur + 1);
  p.status[k] = 'self'; // verification covers the level that was checked, not a higher self-claimed one
  touchStreak();
  save();
  return p.skills[k];
}

/* ---------- Readiness ---------- */
function readiness(p, req) {
  let got = 0, tot = 0;
  const rows = Object.entries(req).map(([k, r]) => {
    const c = p.skills[k] || 0;
    got += Math.min(c, r); tot += r;
    return { k, r, c, state: c >= r ? 'ok' : c > 0 ? 'partial' : 'missing' };
  });
  return { pct: tot ? Math.round(100 * got / tot) : 0, rows };
}

function extractSkills(text) {
  const t = ' ' + String(text).toLowerCase().replace(/[^a-z0-9+#.\- ]/g, ' ').replace(/[.\-]+(?=\s|$)/g, ' ').replace(/\s+/g, ' ') + ' ';
  const out = {};
  Object.entries(SKILLS).forEach(([k, s]) => { if (s.kw.some(w => t.includes(' ' + w + ' '))) out[k] = 3; });
  return out;
}

/* ---------- Resources ---------- */
function recommendResources(p) {
  const gs = gapList(p, p.goal).filter(x => x.g > 0);
  const gmap = {};
  gs.forEach(x => { gmap[x.k] = x.g; });
  const style = p.learn && p.learn.style;
  return S.resources.map(r => {
    const rel = gmap[r.skill] ? Math.min(1, gmap[r.skill] / 3) : 0;
    const s = 0.55 * rel + 0.15 * (r.style === style ? 1 : 0) + 0.3 * Math.min(1, (r.gain || 0) / 4);
    return { r, s, rel };
  }).filter(x => x.rel > 0).sort((a, b) => b.s - a.s);
}

const SYN = {
  noise: ['median', 'filter', 'denoising', 'denoise'], denoise: ['median', 'filter', 'noise'],
  tree: ['trees', 'binary', 'bst'], trees: ['tree', 'binary'], join: ['joins'], joins: ['join'],
  ml: ['machine', 'learning', 'scikit', 'model'], machine: ['ml', 'scikit'], interview: ['communication', 'hr'],
  probability: ['dice', 'conditional', 'stats'], dice: ['probability'], thread: ['process', 'threads'], process: ['thread', 'scheduling'],
};
function tokens(s) { return String(s).toLowerCase().split(/[^a-z0-9+#]+/).filter(Boolean); }
const STOPWORDS = new Set('a an and are as at be by can do does for from how i in is it my of on or so the to we what when where which who why with you your'.split(' '));
function searchScore(query, text) {
  const t = tokens(text); let sc = 0;
  tokens(query).forEach(w => {
    if (STOPWORDS.has(w)) return;
    if (t.includes(w)) sc += 2;
    else if (w.length > 2 && t.some(x => x.startsWith(w))) sc += 1;
    (SYN[w] || []).forEach(s => { if (t.includes(s)) sc += 1; });
  });
  return sc;
}
function effectiveness(r) {
  if ((r.users || 0) < 5) return { label: 'New: still measuring', ok: false };
  return { label: `+${r.gain.toFixed(1)} pts avg improvement (${r.users} students)`, ok: true };
}

/* ---------- Mentor and team matching ---------- */
function mentorMatch(m, p) {
  const gs = gapList(p, p.goal).filter(x => x.g > 0);
  const tot = gs.reduce((a, x) => a + x.g, 0) || 1;
  let K = 0; const why = [];
  gs.forEach(x => {
    const ml = m.skills[x.k] || 0;
    if (ml >= x.r) { K += x.g; why.push(SKILLS[x.k].n); }
    else if (ml > (p.skills[x.k] || 0)) K += x.g * 0.5;
  });
  K /= tot;
  const overlap = m.avail.filter(d => p.avail.includes(d));
  const A = Math.min(1, overlap.length / 2);
  const shared = m.interests.filter(i => p.interests.includes(i));
  const I = (m.goal === p.goal ? 0.6 : 0) + Math.min(0.4, 0.2 * shared.length);
  return { score: 0.5 * K + 0.25 * A + 0.25 * I, K, A, I, overlap, why };
}

function teamScore(c, proj) {
  const owner = person(proj.owner);
  const K = proj.needs.reduce((a, k) => a + Math.min(1, (c.skills[k] || 0) / 4), 0) / proj.needs.length;
  const E = Math.min(1, (c.projects || 0) / 4);
  const A = Math.min(1, c.avail.filter(d => owner.avail.includes(d)).length / 2);
  const I = proj.tags.length ? Math.min(1, c.interests.filter(i => proj.tags.includes(i)).length / Math.max(1, Math.min(2, proj.tags.length))) : 0;
  return { S: 0.45 * K + 0.2 * E + 0.2 * A + 0.15 * I, K, E, A, I };
}
function rankCandidates(proj) {
  return S.people.filter(c => c.role === 'student' && !proj.members.includes(c.id))
    .map(c => Object.assign({ c }, teamScore(c, proj))).sort((a, b) => b.S - a.S);
}
function suggestTeam(proj) {
  const pool = rankCandidates(proj);
  const covered = new Set(proj.needs.filter(k => proj.members.some(m => (person(m).skills[k] || 0) >= 3)));
  const team = [];
  while (team.length < proj.size - proj.members.length && pool.length) {
    let best = null, bv = -1;
    pool.forEach(x => {
      const gain = proj.needs.filter(k => !covered.has(k) && (x.c.skills[k] || 0) >= 3).length;
      const v = x.S + 0.25 * gain;
      if (v > bv) { bv = v; best = x; }
    });
    team.push(best); pool.splice(pool.indexOf(best), 1);
    proj.needs.forEach(k => { if ((best.c.skills[k] || 0) >= 3) covered.add(k); });
  }
  return { team, covered: [...covered], missing: proj.needs.filter(k => !covered.has(k)) };
}

/* ---------- Project ideas ---------- */
function projectIdeas(p) {
  const gaps = new Set(gapList(p, p.goal).filter(x => x.g > 0).map(x => x.k));
  return PROJECT_IDEAS.map(idea => {
    const ks = Object.keys(idea.skills);
    const stretch = ks.filter(k => (p.skills[k] || 0) < idea.skills[k]);
    const maxJump = Math.max(...ks.map(k => idea.skills[k] - (p.skills[k] || 0)));
    const builds = ks.filter(k => gaps.has(k));
    return { idea, stretch, builds, maxJump, fits: maxJump <= 1, score: builds.length * 2 - Math.max(0, maxJump - 1) * 2 + (maxJump <= 0 ? 0.5 : 0) };
  }).sort((a, b) => b.score - a.score);
}

/* ---------- Adaptive aptitude quiz ---------- */
let QZ = null;
function startQuiz() { QZ = { lvl: 2, asked: [], cur: null, n: 8, correct: 0, log: [], picked: null, done: false }; nextQ(); }
function nextQ() {
  const pool = APT.filter(q => !QZ.asked.includes(q.id));
  if (!pool.length || QZ.asked.length >= QZ.n) { QZ.cur = null; QZ.done = true; finishQuiz(); return; }
  pool.sort((a, b) => Math.abs(a.lvl - QZ.lvl) - Math.abs(b.lvl - QZ.lvl));
  QZ.cur = pool[0]; QZ.asked.push(pool[0].id); QZ.picked = null;
}
function answerQ(i) {
  if (!QZ || !QZ.cur || QZ.picked !== null) return;
  const ok = i === QZ.cur.a;
  QZ.picked = i;
  if (ok) QZ.correct++;
  QZ.log.push({ id: QZ.cur.id, topic: QZ.cur.topic, lvl: QZ.cur.lvl, ok });
  QZ.lvl = Math.max(1, Math.min(3, QZ.lvl + (ok ? 1 : -1)));
}
function finishQuiz() {
  if (!QZ.log.length) return;
  S.quiz.history.push({ date: dayStr(new Date()), score: QZ.correct, total: QZ.log.length, topics: clone(QZ.log) });
  touchStreak(); save();
}
function weakTopics(log) {
  const t = {};
  log.forEach(l => { t[l.topic] = t[l.topic] || { a: 0, c: 0 }; t[l.topic].a++; if (l.ok) t[l.topic].c++; });
  return Object.entries(t).map(([topic, v]) => ({ topic, acc: v.c / v.a, a: v.a })).sort((x, y) => x.acc - y.acc);
}

/* ---------- Technical MCQ practice ---------- */
let TQ = null;
function startTech(topic) {
  const items = TECH.filter(q => topic === 'all' || q.skill === topic);
  TQ = { items: items.slice(), i: 0, picked: null, correct: 0, done: false, topic };
}
function answerTech(i) {
  if (!TQ || TQ.done || TQ.picked !== null) return;
  const q = TQ.items[TQ.i];
  TQ.picked = i;
  const ok = i === q.a;
  if (ok) TQ.correct++;
  const st = S.tech.stats[q.skill] || (S.tech.stats[q.skill] = { a: 0, c: 0 });
  st.a++; if (ok) st.c++;
  const p = me();
  if (st.a >= 3 && st.c / st.a >= 0.7 && p.status[q.skill] !== 'faculty') {
    p.skills[q.skill] = Math.max(p.skills[q.skill] || 0, 3);
    p.status[q.skill] = 'assessed';
  }
  touchStreak(); save();
}

/* ---------- Mock interview rubric (rule-based, not a real AI judge) ---------- */
function scoreAnswer(text, kw) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const t = text.toLowerCase();
  const hit = kw.filter(k => t.includes(k));
  const missed = kw.filter(k => !t.includes(k));
  const cov = Math.min(1, hit.length / Math.max(3, Math.ceil(kw.length * 0.5)));
  const len = Math.min(1, words.length / 45);
  const clar = /(for example|for instance|e\.g\.|because|so that|which means|\d)/.test(t) ? 1 : 0.3;
  return { score: Math.round((0.5 * cov + 0.3 * len + 0.2 * clar) * 100), hit, missed, words: words.length, cov, len, clar };
}
let IV = null;

/* ---------- Alerts ---------- */
function alerts(p) {
  const a = [];
  const gs = gapList(p, p.goal).filter(x => x.g > 0).sort((x, y) => y.g - x.g);
  if (gs[0]) a.push({ t: 'warn', m: `Biggest gap for ${p.goal}: ${SKILLS[gs[0].k].n} (you are at level ${gs[0].c}, the role needs ${gs[0].r}).` });
  (p.grades || []).filter(g => g.g < 65).forEach(g => a.push({ t: 'bad', m: `${g.s} is at ${g.g}%. Suggested rescue plan: one practice set plus a mentor session this week.` }));
  const open = S.questions.filter(q => q.by === p.id && !q.answers.length).length;
  if (open) a.push({ t: 'ok', m: `${open} of your questions are still waiting for an answer.` });
  const acc = S.requests.filter(r => r.from === p.id && r.status === 'accepted' && r.post == null).length;
  if (acc) a.push({ t: '', m: `${acc} accepted mentor session(s): log your before/after scores to measure improvement.` });
  return a;
}

/* ---------- Charts (inline SVG / CSS) ---------- */
function radar(labels, series, max) {
  max = max || 5;
  const n = labels.length, cx = 170, cy = 160, R = 105;
  const pt = (i, v) => { const a = -Math.PI / 2 + 2 * Math.PI * i / n; const r = R * v / max; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const f = x => x.toFixed(1);
  let g = '';
  for (let l = 1; l <= max; l++) g += `<polygon points="${labels.map((_, i) => pt(i, l).map(f).join(',')).join(' ')}" fill="none" stroke="#e4e7f1"/>`;
  labels.forEach((lb, i) => {
    const e = pt(i, max), t = pt(i, max + 0.95);
    g += `<line x1="${cx}" y1="${cy}" x2="${f(e[0])}" y2="${f(e[1])}" stroke="#e4e7f1"/>`;
    g += `<text x="${f(t[0])}" y="${f(t[1])}" font-size="10" text-anchor="middle" dominant-baseline="middle" fill="#6b7188">${esc(lb)}</text>`;
  });
  series.forEach(s => {
    g += `<polygon points="${s.vals.map((v, i) => pt(i, v).map(f).join(',')).join(' ')}" fill="${s.color}" fill-opacity=".16" stroke="${s.color}" stroke-width="2"/>`;
  });
  const legend = series.map(s => `<span class="chip"><span style="color:${s.color}">●</span> ${esc(s.name)}</span>`).join('');
  return `<svg viewBox="0 0 340 320" width="100%" role="img" aria-label="Skill radar chart: ${esc(series.map(s => s.name).join(' vs '))}">${g}</svg><div style="text-align:center">${legend}</div>`;
}

function lineChart(values, labels) {
  if (!values.length) return '<div class="empty">No data yet.</div>';
  const W = 420, H = 150, pad = 26;
  const x = i => values.length === 1 ? W / 2 : pad + i * (W - 2 * pad) / (values.length - 1);
  const y = v => H - pad - (v / 100) * (H - 2 * pad);
  let g = [0, 50, 100].map(v => `<line x1="${pad}" x2="${W - pad}" y1="${y(v)}" y2="${y(v)}" stroke="#e4e7f1"/><text x="2" y="${y(v) + 3}" font-size="9" fill="#6b7188">${v}</text>`).join('');
  g += `<polyline fill="none" stroke="#4f46e5" stroke-width="2.5" points="${values.map((v, i) => x(i) + ',' + y(v)).join(' ')}"/>`;
  values.forEach((v, i) => { g += `<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="#4f46e5"/><text x="${x(i)}" y="${H - 6}" font-size="9" text-anchor="middle" fill="#6b7188">${esc((labels && labels[i]) || i + 1)}</text>`; });
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Score trend chart">${g}</svg>`;
}

function bars(items, cls) {
  return items.map(i => `<div style="margin:.45rem 0"><div class="row between"><span>${esc(i.label)}</span><b>${i.value}%</b></div><div class="bar ${cls || ''}"><i style="width:${Math.max(0, Math.min(100, i.value))}%"></i></div></div>`).join('');
}
const lvlBar = (c, t) => `<span class="lvl" role="img" aria-label="Level ${c} of 5${t ? ', target ' + t : ''}">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= c ? 'f' : (t && i <= t ? 't' : '')}"></i>`).join('')}</span>`;
const pct = v => Math.round(v * 100) + '%';
