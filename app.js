/* ALPG app shell: router, events and actions. */

function toast(msg) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 2600);
}

function parseHash() {
  const parts = (location.hash || '').replace(/^#\/?/, '').split('/').filter(Boolean);
  return [parts[0] || '', parts[1] || ''];
}
function go(route) { if (location.hash === '#/' + route) render(); else location.hash = '#/' + route; }

function render() {
  if (!S.session || !person(S.session.uid)) {
    document.body.classList.add('auth');
    AUTH.mode = parseHash()[0] === 'register' ? 'register' : 'login';
    $('#view').innerHTML = authPage();
    return;
  }
  document.body.classList.remove('auth');
  S.meId = S.session.uid; S.role = person(S.meId).role;
  const role = S.role;
  let [route, param] = parseHash();
  if (!route || !pages[route] || !allowed(route, role)) { route = DEFAULT_ROUTE[role]; param = ''; }
  $('#nav').innerHTML = NAV.map(g => {
    const items = g.items.filter(i => i.r.includes(role));
    return items.length ? `<div class="grp">${g.g}</div>` + items.map(i => `<a href="#/${i.id}" class="${i.id === route ? 'active' : ''}" ${i.id === route ? 'aria-current="page"' : ''}><span class="ic" aria-hidden="true">${i.i}</span>${i.l}</a>`).join('') : '';
  }).join('');
  const p = me();
  $('#crumb').textContent = navLabel(route);
  $('#who').innerHTML = `${avatar(p)}<span><b>${esc(p.name)}</b><br><small>${esc(role)}</small></span>`;
  $('#view').innerHTML = pages[route](param);
  const sb = $('#sidebar'); if (sb) sb.classList.remove('open');
}

/* ---------- Actions (click) ---------- */
const actions = {
  toggleMenu() { $('#sidebar').classList.toggle('open'); },
  resetData() { if (typeof confirm === 'function' && !confirm('Reset all demo data? This also removes accounts you created.')) return; resetState(); QZ = null; TQ = null; IV = null; AUTH = { mode: 'login', err: '', busy: false }; location.hash = '#/login'; render(); toast('Demo data reset'); },
  logout() { logout(); QZ = null; TQ = null; IV = null; AUTH = { mode: 'login', err: '', busy: false }; if (location.hash === '#/login') render(); else location.hash = '#/login'; },
  authMode(d) { AUTH.err = ''; const h = '#/' + d.m; if (location.hash === h) render(); else location.hash = h; },
  fillDemo(d) { const e = $('#loginEmail'), p = $('#loginPw'); if (e) e.value = d.e; if (p) p.value = 'demo123'; if (p && p.focus) p.focus(); },
  reqVerify(d) {
    if (S.verify.some(v => v.uid === S.meId && v.skill === d.k)) return;
    S.verify.push({ uid: S.meId, skill: d.k, note: 'Requested via Skill Passport. Evidence to be reviewed.' });
    save(); toast('Verification requested. Faculty will review it.'); render();
  },
  completeStep(d) {
    const lv = completeStep(d.k); toast(`${skillName(d.k)} is now level ${lv} (self-reported)`); render();
    pushToServer('PUT', '/api/skills/' + d.k, { level: lv }).then(r => {
      if (!r) return;
      if (r.status === 401) { render(); return; }
      if (!r.ok && r.status !== 0) toast('Saved here, but the server said: ' + r.message);
    });
  },
  bookmark(d) {
    const i = S.bookmarks.indexOf(d.id);
    if (i >= 0) S.bookmarks.splice(i, 1); else S.bookmarks.push(d.id);
    save(); render();
  },
  vote(d) {
    const q = S.questions.find(x => x.id === d.q), a = q && q.answers.find(x => x.id === d.a);
    if (!a) return;
    S.voted = S.voted || {};
    const key = S.meId + ':' + a.id;
    if (S.voted[key]) { toast('You already voted on this answer'); return; }
    if (a.by === S.meId) { toast('You cannot vote on your own answer'); return; }
    S.voted[key] = 1; a.votes++; person(a.by).rep += 2; save(); render();
  },
  accept(d) {
    const q = S.questions.find(x => x.id === d.q);
    if (!q || q.by !== S.meId) return;
    q.answers.forEach(x => { x.accepted = false; });
    const a = q.answers.find(x => x.id === d.a); a.accepted = true; person(a.by).rep += 15;
    save(); toast('Answer accepted'); render();
  },
  verifyAns(d) {
    if (S.role !== 'faculty') return;
    const q = S.questions.find(x => x.id === d.q), a = q.answers.find(x => x.id === d.a);
    a.verified = true; person(a.by).rep += 10; save(); toast('Marked as faculty-verified'); render();
  },
  reqAccept(d) { const r = S.requests.find(x => x.id === d.rid); if (r) { r.status = 'accepted'; save(); toast('Request accepted'); render(); } },
  reqDecline(d) { const r = S.requests.find(x => x.id === d.rid); if (r) { r.status = 'declined'; save(); render(); } },
  joinProject(d) {
    const pr = S.projects.find(x => x.id === d.id);
    if (pr && !pr.invites.some(i => i.uid === S.meId)) { pr.invites.push({ uid: S.meId, kind: 'join' }); save(); toast('Request sent to the project owner'); render(); }
  },
  invite(d) {
    const pr = S.projects.find(x => x.id === d.id);
    if (pr && !pr.invites.some(i => i.uid === d.u)) { pr.invites.push({ uid: d.u, kind: 'invite' }); save(); toast('Invitation sent (they must accept)'); render(); }
  },
  startIdea(d) {
    const idea = PROJECT_IDEAS.find(x => x.title === d.t);
    if (!idea) return;
    idea.milestones.forEach(m => S.tasks.push({ id: uid('tk'), text: `${idea.title}: ${m}`, done: false }));
    save(); toast('Milestones added to your planner');
  },
  setGoal(d) { me().goal = d.r; save(); toast('Target role updated'); render(); pushToServer('PUT', '/api/profile', { goal: d.r }); },
  quizStart() { startQuiz(); render(); },
  quizExit() { QZ = null; render(); },
  quizAns(d) { answerQ(Number(d.i)); render(); },
  quizNext() { nextQ(); render(); },
  techStart(d) { startTech(d.t); if (!TQ.items.length) { toast('No questions for that topic'); TQ = null; } render(); },
  techAns(d) { answerTech(Number(d.i)); render(); },
  techNext() { if (TQ.i + 1 >= TQ.items.length) { TQ.done = true; } else { TQ.i++; TQ.picked = null; } render(); },
  codeToggle(d) {
    const i = S.coding.indexOf(d.id);
    if (i >= 0) S.coding.splice(i, 1); else { S.coding.push(d.id); touchStreak(); }
    save(); render();
  },
  ivStart(d) { IV = { type: d.t, i: 0, res: [], fb: null, done: false, avg: 0 }; render(); },
  ivExit() { IV = null; render(); },
  ivNext() {
    const qs = INTERVIEW[IV.type];
    if (IV.i + 1 >= qs.length) {
      IV.done = true;
      IV.avg = Math.round(IV.res.reduce((a, r) => a + r.score, 0) / IV.res.length);
      S.interviews.push({ type: IV.type, avg: IV.avg, date: dayStr(new Date()) });
      touchStreak(); save();
    } else { IV.i++; IV.fb = null; }
    render();
  },
  taskDel(d) { S.tasks = S.tasks.filter(t => t.id !== d.id); save(); render(); },
  group(d) {
    const i = S.groups.indexOf(d.id);
    if (i >= 0) S.groups.splice(i, 1); else S.groups.push(d.id);
    save(); render();
  },
  verifyOk(d) {
    const v = S.verify[Number(d.i)];
    if (!v) return;
    const u = person(v.uid); u.status[v.skill] = 'faculty';
    S.verify.splice(Number(d.i), 1); save(); toast('Skill verified'); render();
  },
  verifyNo(d) { S.verify.splice(Number(d.i), 1); save(); render(); },
};

/* ---------- Change handlers ---------- */
const changes = {
  goal(el) { me().goal = el.value; save(); render(); pushToServer('PUT', '/api/profile', { goal: el.value }); },
  rate(el) {
    const n = Number(el.value); if (!n) return;
    const r = S.resources.find(x => x.id === el.dataset.id); if (!r) return;
    const old = S.ratings[r.id];
    if (old) { r.rating = r.votes > 1 ? (r.rating * r.votes - old + n) / r.votes : n; }
    else { r.rating = (r.rating * r.votes + n) / (r.votes + 1); r.votes++; }
    S.ratings[r.id] = n; save(); toast('Thanks for rating'); render();
  },
  task(el) { const t = S.tasks.find(x => x.id === el.dataset.id); if (t) { t.done = el.checked; save(); render(); } },
};

/* ---------- Form handlers ---------- */
const forms = {
  async login(f) {
    if (AUTH.busy) return;
    AUTH.busy = true;
    try {
      const email = f.get('email') || '', pw = f.get('pw') || '';
      let id = null;
      if (API.online) {
        const r = await serverLogin(email, pw);
        if (r.err) { AUTH.err = r.err; render(); return; }
        if (r.ok) id = r.id;            // r.offline: server vanished, fall back to the local check below
      }
      if (!id) {
        id = attemptLogin(email, pw);
        if (!id) { AUTH.err = 'Incorrect email or password.'; render(); return; }
        login(id);
      }
      AUTH.err = ''; location.hash = '#/' + DEFAULT_ROUTE[person(id).role]; render(); toast('Signed in as ' + person(id).name);
    } finally { AUTH.busy = false; }
  },
  async register(f) {
    if (AUTH.busy) return;
    AUTH.busy = true;
    try {
      const o = { name: f.get('name'), email: f.get('email'), pw: f.get('pw'), pw2: f.get('pw2'), year: f.get('year'), branch: f.get('branch'), goal: f.get('goal') };
      if (o.pw !== o.pw2) { AUTH.err = 'Passwords do not match.'; AUTH.mode = 'register'; render(); return; }
      let id = null;
      if (API.online) {
        const r = await serverRegister(o);
        if (r.err) { AUTH.err = r.err; AUTH.mode = 'register'; render(); return; }
        if (r.ok) id = r.id;
      }
      if (!id) {
        const r = registerUser(o);
        if (r.err) { AUTH.err = r.err; AUTH.mode = 'register'; render(); return; }
        id = r.uid; login(id);
      }
      AUTH.err = ''; location.hash = '#/dashboard'; render(); toast('Account created. Welcome!');
    } finally { AUTH.busy = false; }
  },
  resFilter(f) { RES = { q: f.get('q').trim(), type: f.get('type'), skill: f.get('skill'), sort: f.get('sort') }; render(); },
  upload(f) {
    S.resources.unshift({ id: uid('r'), title: f.get('title').trim(), type: f.get('type'), skill: f.get('skill'), topic: f.get('topic').trim(), by: S.meId, style: 'Read/Write', rating: 0, votes: 0, users: 0, gain: 0 });
    person(S.meId).rep += 5; save(); toast('Published. Effectiveness appears after 5 students use it.'); render();
  },
  qaSearch(f) { QAF.q = f.get('q').trim(); render(); },
  ask(f) {
    const id = uid('q');
    S.questions.unshift({ id, title: f.get('title').trim(), body: f.get('body').trim(), subject: f.get('subject').trim(), topic: f.get('topic').trim(), by: S.meId, when: 'just now', answers: [] });
    save(); toast('Question posted'); go('qa/' + id);
  },
  answer(f, d) {
    const q = S.questions.find(x => x.id === d.q); if (!q) return;
    q.answers.push({ id: uid('a'), by: S.meId, text: f.get('text').trim(), votes: 0, accepted: false, verified: false });
    person(S.meId).rep += 3; save(); toast('Answer posted'); render();
  },
  mentorReq(f, d) {
    S.requests.push({ id: uid('m'), from: S.meId, to: d.to, topic: f.get('topic'), slot: f.get('slot'), msg: f.get('msg').trim(), status: 'pending', pre: null, post: null });
    save(); toast('Request sent'); render();
  },
  prepost(f, d) {
    const r = S.requests.find(x => x.id === d.rid); if (!r) return;
    r.pre = Math.max(0, Math.min(10, Number(f.get('pre')))); r.post = Math.max(0, Math.min(10, Number(f.get('post'))));
    save(); toast('Improvement recorded'); render();
  },
  project(f) {
    const needs = f.getAll('needs');
    if (!needs.length) { toast('Pick at least one skill'); return; }
    const id = uid('p');
    S.projects.unshift({ id, title: f.get('title').trim(), desc: f.get('desc').trim(), owner: S.meId, needs, tags: f.get('tags').split(',').map(s => s.trim()).filter(Boolean), size: Math.max(2, Math.min(6, Number(f.get('size')) || 3)), timeline: f.get('timeline').trim() || 'TBD', members: [S.meId], invites: [] });
    save(); toast('Project posted'); go('projects/' + id);
  },
  readiness(f) { RDY = { role: f.get('role'), jd: f.get('jd') }; render(); },
  ivAnswer(f) {
    const q = INTERVIEW[IV.type][IV.i];
    IV.fb = scoreAnswer(f.get('text'), q.kw); IV.res.push(IV.fb); render();
  },
  task(f) { S.tasks.unshift({ id: uid('tk'), text: f.get('text').trim(), done: false }); save(); render(); },
};

/* ---------- Wiring ---------- */
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('click', e => {
    const t = e.target.closest && e.target.closest('[data-act]');
    if (t && actions[t.dataset.act]) { e.preventDefault(); actions[t.dataset.act](t.dataset, t); }
  });
  document.addEventListener('change', e => {
    const t = e.target;
    if (t && t.dataset && t.dataset.change && changes[t.dataset.change]) changes[t.dataset.change](t);
  });
  document.addEventListener('submit', e => {
    const f = e.target;
    if (f && f.dataset && f.dataset.form && forms[f.dataset.form]) { e.preventDefault(); forms[f.dataset.form](new FormData(f), f.dataset); }
  });
  document.addEventListener('input', e => {
    const t = e.target;
    if (t && t.dataset && t.dataset.input === 'similar') { const box = $('#similar'); if (box) box.innerHTML = similarHtml(t.value); }
  });
  window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
  render();
  // Look for a backend; if one answers, check a saved sign-in is still valid and refresh skills from it.
  API.probe().then(async () => {
    if (API.online && S.session && S.token) {
      const r = await API.call('GET', '/api/auth/me', null, S.token);
      if (r.status === 401) { logout(); AUTH.err = 'Your session expired. Please sign in again.'; }
      else if (r.ok) {
        const p = me();
        p.skills = {}; p.status = {};
        Object.entries(r.data.skills).forEach(([k, v]) => { p.skills[k] = v.level; p.status[k] = v.status; });
        save();
      }
    }
    render();
  });
}
