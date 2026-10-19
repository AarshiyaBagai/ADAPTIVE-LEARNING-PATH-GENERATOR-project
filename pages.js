/* ALPG pages: each function returns an HTML string for the main view. */

const CODING = [
  { id: 'c1', t: 'Two Sum', d: 'Easy', topic: 'Arrays / Hash map' },
  { id: 'c2', t: 'Valid Parentheses', d: 'Easy', topic: 'Stack' },
  { id: 'c3', t: 'Reverse a Linked List', d: 'Easy', topic: 'Linked list' },
  { id: 'c4', t: 'Longest Substring Without Repeating Characters', d: 'Medium', topic: 'Sliding window' },
  { id: 'c5', t: 'Binary Tree Level Order Traversal', d: 'Medium', topic: 'Trees / BFS' },
  { id: 'c6', t: 'Number of Islands', d: 'Medium', topic: 'Graphs / DFS' },
  { id: 'c7', t: 'Second Highest Salary (SQL)', d: 'Medium', topic: 'SQL' },
  { id: 'c8', t: 'LRU Cache', d: 'Hard', topic: 'Design / Hash map + list' },
];

const NAV = [
  { g: 'Learn', items: [
    { id: 'dashboard', l: 'Dashboard', i: '🏠', r: ['student', 'senior'] },
    { id: 'passport', l: 'Skill Passport', i: '🪪', r: ['student', 'senior'] },
    { id: 'pathway', l: 'Learning Pathway', i: '🧭', r: ['student'] },
    { id: 'resources', l: 'Resource Hub', i: '📚', r: ['student', 'senior', 'faculty'] },
    { id: 'planner', l: 'Planner & Groups', i: '🗓️', r: ['student'] },
  ] },
  { g: 'Community', items: [
    { id: 'qa', l: 'Q&A Forum', i: '💬', r: ['student', 'senior', 'faculty'] },
    { id: 'mentors', l: 'Mentorship', i: '🤝', r: ['student', 'senior'] },
    { id: 'projects', l: 'Projects & Teams', i: '👥', r: ['student', 'senior'] },
    { id: 'ideas', l: 'Project Generator', i: '💡', r: ['student'] },
  ] },
  { g: 'Career', items: [
    { id: 'readiness', l: 'Internship Readiness', i: '🎯', r: ['student'] },
    { id: 'aptitude', l: 'Aptitude Prep', i: '🧮', r: ['student'] },
    { id: 'technical', l: 'Technical Practice', i: '⌨️', r: ['student'] },
    { id: 'interview', l: 'Mock Interview', i: '🎤', r: ['student'] },
  ] },
  { g: 'Insights', items: [
    { id: 'faculty', l: 'Faculty Dashboard', i: '📊', r: ['faculty'] },
  ] },
];
const DEFAULT_ROUTE = { student: 'dashboard', senior: 'dashboard', faculty: 'faculty' };
function allowed(route, role) { return NAV.some(g => g.items.some(i => i.id === route && i.r.includes(role))); }
function navLabel(route) { for (const g of NAV) for (const i of g.items) if (i.id === route) return i.l; return 'ALPG'; }

const head = (t, s) => `<div class="page-head"><h1>${t}</h1>${s ? `<p>${s}</p>` : ''}</div>`;
const skillName = k => (SKILLS[k] ? SKILLS[k].n : k);
const statusBadge = s => { const x = STATUS[s || 'self']; return `<span class="badge ${x.c}">${x.t}</span>`; };
const roleSelect = (name, cur) => `<select name="${name}" class="inline" data-change="${name === 'goal' ? 'goal' : ''}">${Object.keys(ROLES).map(r => `<option ${r === cur ? 'selected' : ''}>${esc(r)}</option>`).join('')}</select>`;

/* ---------- Dashboard ---------- */
function dashboard() {
  return S.role === 'senior' ? dashboardSenior() : dashboardStudent();
}

function dashboardStudent() {
  const p = me(), req = ROLES[p.goal].req, keys = Object.keys(req);
  const rd = readiness(p, req), steps = pathway(p, p.goal).slice(0, 3);
  const recs = recommendResources(p).slice(0, 3), al = alerts(p);
  const verified = Object.values(p.status).filter(s => s !== 'self').length;
  return head(`Welcome back, ${esc(p.name.split(' ')[0])} 👋`, `Your target role: <b>${esc(p.goal)}</b>. Your plan updates whenever you add evidence.`) + `
  <div class="grid g4">
    <div class="card stat"><b>${rd.pct}%</b><span>Readiness for ${esc(p.goal)}</span><div class="bar"><i style="width:${rd.pct}%"></i></div></div>
    <div class="card stat"><b>${verified}</b><span>Skills backed by evidence</span></div>
    <div class="card stat"><b>🔥 ${S.streak.days}</b><span>Day learning streak</span></div>
    <div class="card stat"><b>${p.rep}</b><span>Community reputation</span></div>
  </div>
  <div class="grid g-main" style="margin-top:1rem">
    <div class="stack">
      <div class="card"><div class="row between"><h2>Your next steps</h2><a href="#/pathway">Full pathway →</a></div>
        ${steps.length ? steps.map(s => `<div class="row between" style="padding:.5rem 0;border-bottom:1px solid var(--line)"><div><b>${esc(skillName(s.k))}</b><br><small>Level ${s.from} → ${s.target} · ${esc(s.why)}</small></div><span class="badge ${s.state === 'current' ? '' : s.state === 'locked' ? 'grey' : 'warn'}">${s.state === 'current' ? 'Start here' : s.state === 'locked' ? 'Locked' : 'Up next'}</span></div>`).join('') : '<div class="empty">🎉 You meet every requirement for this role.</div>'}
      </div>
      <div class="card"><div class="row between"><h2>Recommended for your gaps</h2><a href="#/resources">Resource hub →</a></div>
        ${recs.length ? recs.map(x => resourceMini(x.r)).join('') : '<div class="empty">No gaps to fill. Nice work.</div>'}
      </div>
      <div class="card"><h2>Alerts</h2>${al.length ? al.map(a => `<div class="callout ${a.t}" style="margin:.4rem 0">${esc(a.m)}</div>`).join('') : '<div class="empty">Nothing needs your attention.</div>'}</div>
    </div>
    <div class="stack">
      <div class="card"><h2>Skills vs target</h2>${radar(keys.map(k => SHORT[k]), [{ name: 'You', vals: keys.map(k => p.skills[k] || 0), color: '#4f46e5' }, { name: 'Target', vals: keys.map(k => req[k]), color: '#16a34a' }])}</div>
      <div class="card"><h2>Subject performance</h2>
        <div class="grid g2" style="gap:.5rem">${p.grades.map(g => `<div style="padding:.6rem;border-radius:10px;background:${g.g >= 80 ? 'var(--ok-soft)' : g.g >= 65 ? 'var(--warn-soft)' : 'var(--bad-soft)'}"><b>${g.g}%</b><br><small>${esc(g.s)}</small></div>`).join('')}</div>
        <small>Grades are entered manually in this demo. Only you and faculty can see them.</small></div>
    </div>
  </div>`;
}

function resourceMini(r) {
  const e = effectiveness(r), a = person(r.by);
  return `<div class="row between" style="padding:.5rem 0;border-bottom:1px solid var(--line)"><div><b>${esc(r.title)}</b><br><small>${esc(r.type)} · ${esc(skillName(r.skill))} · by ${esc(a ? a.name : 'Unknown')}</small></div><span class="badge ${e.ok ? 'ok' : 'grey'}">${e.ok ? '+' + r.gain.toFixed(1) + ' pts' : 'New'}</span></div>`;
}

function dashboardSenior() {
  const p = me();
  const inbox = S.requests.filter(r => r.to === p.id);
  const pend = inbox.filter(r => r.status === 'pending').length;
  const done = inbox.filter(r => r.post != null);
  const avg = done.length ? (done.reduce((a, r) => a + (r.post - r.pre), 0) / done.length).toFixed(1) : '–';
  const mine = S.resources.filter(r => r.by === p.id);
  return head(`Welcome, ${esc(p.name.split(' ')[0])} 👋`, 'Your impact as a mentor and contributor.') + `
  <div class="grid g4">
    <div class="card stat"><b>${pend}</b><span>Pending mentor requests</span></div>
    <div class="card stat"><b>${p.mentees + inbox.filter(r => r.status === 'accepted').length}</b><span>Mentees helped</span></div>
    <div class="card stat"><b>${avg}</b><span>Avg score improvement (pts)</span></div>
    <div class="card stat"><b>${p.rep}</b><span>Reputation</span></div>
  </div>
  <div class="card" style="margin-top:1rem"><div class="row between"><h2>Request inbox</h2><a href="#/mentors">Open inbox →</a></div>
    ${pend ? `<p>You have <b>${pend}</b> new request(s) waiting for a response.</p>` : '<div class="empty">No pending requests. Students find you through the mentor match list.</div>'}</div>
  <div class="card"><h2>How your shared resources perform</h2>
    <table class="table"><thead><tr><th>Resource</th><th>Rating</th><th>Effect on scores</th></tr></thead><tbody>
    ${mine.map(r => { const e = effectiveness(r); return `<tr><td>${esc(r.title)}</td><td>★ ${r.rating.toFixed(1)}</td><td><span class="badge ${e.ok ? 'ok' : 'grey'}">${esc(e.label)}</span></td></tr>`; }).join('') || '<tr><td colspan="3" class="muted">You have not shared anything yet.</td></tr>'}
    </tbody></table></div>`;
}

/* ---------- Skill Passport ---------- */
function passport() {
  const p = me(), ks = Object.keys(p.skills).sort((a, b) => p.skills[b] - p.skills[a]);
  const mentorDone = S.requests.filter(r => r.to === p.id && r.status === 'accepted').length;
  const myAnswers = S.questions.reduce((a, q) => a + q.answers.filter(x => x.by === p.id).length, 0);
  const pending = S.verify.filter(v => v.uid === p.id).map(v => v.skill);
  const rd = p.role === 'student' ? readiness(p, ROLES[p.goal].req) : null;
  return head('Skill Passport', 'A living record of what you can demonstrate, not just your CGPA.') + `
  <div class="grid g-main">
    <div class="stack">
      <div class="card"><div class="row">${avatar(p, 'lg')}<div><h2 style="margin:0">${esc(p.name)}</h2><small>${esc(p.branch)} · Year ${p.year} · Goal: ${esc(p.goal)}</small></div></div></div>
      <div class="card"><h2>Skills &amp; evidence</h2>
        <small>Self-reported skills count for less than assessed or faculty-verified ones.</small>
        ${ks.map(k => `<div class="skill-row"><span>${esc(skillName(k))}</span>${lvlBar(p.skills[k])}<span class="row" style="gap:.4rem">${statusBadge(p.status[k])}${p.status[k] !== 'faculty' && !pending.includes(k) && S.role === 'student' ? `<button class="btn ghost small" data-act="reqVerify" data-k="${k}">Request verification</button>` : ''}${pending.includes(k) ? '<span class="badge warn">Verification pending</span>' : ''}</span></div>`).join('')}
      </div>
    </div>
    <div class="stack">
      <div class="card"><h2>Activity record</h2>
        <div class="row between"><span>Projects</span><b>${p.projects}</b></div>
        <div class="row between"><span>Answers posted</span><b>${myAnswers}</b></div>
        <div class="row between"><span>Mentor sessions given</span><b>${mentorDone + (p.mentees || 0)}</b></div>
        <div class="row between"><span>Mock interviews</span><b>${p.id === 'u1' ? S.interviews.length : '–'}</b></div>
        <div class="row between"><span>Aptitude tests</span><b>${p.id === 'u1' ? S.quiz.history.length : '–'}</b></div></div>
      ${rd ? `<div class="card"><h2>Readiness: ${esc(p.goal)}</h2><div class="row"><div class="score-ring" style="--p:${rd.pct}"><b>${rd.pct}%</b></div><small>Based on demonstrated levels vs the role's requirements.</small></div></div>` : ''}
    </div>
  </div>`;
}

/* ---------- Pathway ---------- */
function pathwayPage() {
  const p = me(), steps = pathway(p, p.goal), rd = readiness(p, ROLES[p.goal].req);
  const ments = S.people.filter(x => x.role === 'senior');
  return head('Adaptive Learning Pathway', 'Prerequisite-aware roadmap built from the gap between your skills and your target role.') + `
  <div class="card row between"><div class="row"><label class="f" style="min-width:230px">Target role${roleSelect('goal', p.goal)}</label><small style="max-width:360px">${esc(ROLES[p.goal].desc)}</small></div>
    <div class="row"><div class="score-ring" style="--p:${rd.pct};width:84px;height:84px"><b style="font-size:1.1rem">${rd.pct}%</b></div><small>role readiness</small></div></div>
  <div class="callout" style="margin:1rem 0">Gap formula: <b>gap = max(0, required level − your level)</b>. Prerequisites below level 2 are added automatically and ordered first (topological sort of the skill graph).</div>
  <div class="timeline">
  ${steps.length ? steps.map((s, i) => {
    const res = S.resources.filter(r => r.skill === s.k).sort((a, b) => b.gain - a.gain).slice(0, 2);
    const mentor = ments.filter(m => (m.skills[s.k] || 0) >= s.target).sort((a, b) => b.rating - a.rating)[0];
    return `<div class="step ${s.state === 'current' ? 'current' : s.state === 'locked' ? 'locked' : ''}">
      <div class="row between"><div><b>${i + 1}. ${esc(skillName(s.k))}</b> <span class="badge ${s.state === 'current' ? '' : s.state === 'locked' ? 'grey' : 'warn'}">${s.state === 'current' ? 'Current' : s.state === 'locked' ? 'Locked: finish prerequisites' : 'Up next'}</span><br><small>${esc(s.why)} · gap ${s.target - s.from}</small></div>
        <div class="row">${lvlBar(s.from, s.target)}<button class="btn small" data-act="completeStep" data-k="${s.k}" ${s.state === 'locked' ? 'disabled' : ''}>Log practice +1</button></div></div>
      ${res.length ? `<div style="margin-top:.5rem"><small>Resources: </small>${res.map(r => `<span class="chip">${esc(r.title)}</span>`).join('')}</div>` : ''}
      ${mentor ? `<small>Mentor who can help: <b>${esc(mentor.name)}</b> (${esc(skillName(s.k))} level ${mentor.skills[s.k]}) · <a href="#/mentors">find a session</a></small>` : ''}
    </div>`;
  }).join('') : '<div class="card empty">🎉 No gaps left for this role. Try a harder target role.</div>'}
  </div>
  <small>Logging practice marks the skill as self-reported. Take a technical quiz or ask faculty to verify to strengthen the evidence.</small>`;
}

/* ---------- Resources ---------- */
let RES = { q: '', type: '', skill: '', sort: 'rel' };
function resources() {
  const p = me();
  let list = S.resources.map(r => ({ r, sc: RES.q ? searchScore(RES.q, [r.title, r.topic, skillName(r.skill), r.type].join(' ')) : 1 }));
  if (RES.q) list = list.filter(x => x.sc > 0);
  if (RES.type) list = list.filter(x => x.r.type === RES.type);
  if (RES.skill) list = list.filter(x => x.r.skill === RES.skill);
  const recSet = {}; if (p.role === 'student') recommendResources(p).forEach(x => { recSet[x.r.id] = x.s; });
  list.sort((a, b) => RES.sort === 'eff' ? b.r.gain - a.r.gain : RES.sort === 'rating' ? b.r.rating - a.r.rating : (b.sc - a.sc) || ((recSet[b.r.id] || 0) - (recSet[a.r.id] || 0)));
  const types = [...new Set(S.resources.map(r => r.type))];
  return head('Resource Hub', 'Notes, videos and practice sets shared by seniors and faculty, ranked by how much they actually help.') + `
  <div class="card"><form data-form="resFilter" class="row" style="align-items:end">
    <label class="f" style="flex:2;min-width:200px">Search (try "remove noise from image")<input name="q" value="${esc(RES.q)}" placeholder="Search topics, skills, titles"></label>
    <label class="f">Type<select name="type"><option value="">All</option>${types.map(t => `<option ${RES.type === t ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></label>
    <label class="f">Skill<select name="skill"><option value="">All</option>${Object.keys(SKILLS).map(k => `<option value="${k}" ${RES.skill === k ? 'selected' : ''}>${esc(SKILLS[k].n)}</option>`).join('')}</select></label>
    <label class="f">Sort<select name="sort"><option value="rel" ${RES.sort === 'rel' ? 'selected' : ''}>Best match</option><option value="eff" ${RES.sort === 'eff' ? 'selected' : ''}>Most effective</option><option value="rating" ${RES.sort === 'rating' ? 'selected' : ''}>Top rated</option></select></label>
    <button class="btn">Apply</button></form>
    <small>Search uses keywords plus a small synonym map. A production version would use embeddings.</small></div>
  <div class="grid g-main" style="margin-top:1rem"><div class="stack">
    ${list.length ? list.map(x => resourceCard(x.r, recSet[x.r.id])).join('') : '<div class="card empty">No resources match. Try different words.</div>'}
  </div>
  <div class="stack"><div class="card"><h2>Share your notes</h2>
    <form data-form="upload" class="grid-f">
      <label class="f">Title<input name="title" required maxlength="90"></label>
      <label class="f">Skill / subject<select name="skill">${Object.keys(SKILLS).map(k => `<option value="${k}">${esc(SKILLS[k].n)}</option>`).join('')}</select></label>
      <label class="f">Topic<input name="topic" required maxlength="40"></label>
      <label class="f">Type<select name="type"><option>Notes</option><option>Video</option><option>Practice</option><option>Article</option></select></label>
      <label class="f">File (demo only: not uploaded)<input type="file" name="file"></label>
      <button class="btn">Publish</button></form></div>
    <div class="callout">Effectiveness = average post-test minus pre-test score of students who used the resource. It needs at least 5 users, and it shows association, not proof of cause.</div></div></div>`;
}

function resourceCard(r, recScore) {
  const a = person(r.by), e = effectiveness(r), saved = S.bookmarks.includes(r.id), mine = S.ratings[r.id];
  return `<div class="card"><div class="row between"><div><b>${esc(r.title)}</b><br><small>${esc(r.type)} · ${esc(skillName(r.skill))} · ${esc(r.topic)} · for ${esc(r.style)} learners</small></div>
    ${recScore ? '<span class="badge">Fills a gap</span>' : ''}</div>
    <div class="row between" style="margin-top:.6rem"><div class="row"><span class="row" style="gap:.4rem">${a ? avatar(a) : ''}<small>${esc(a ? a.name : 'Unknown')}</small></span><span class="badge warn">★ ${r.rating.toFixed(1)} (${r.votes})</span><span class="badge ${e.ok ? 'ok' : 'grey'}">${esc(e.label)}</span></div>
    <div class="row"><select class="inline" data-change="rate" data-id="${r.id}" aria-label="Rate this resource"><option value="">${mine ? 'Your rating: ' + mine : 'Rate'}</option>${[5, 4, 3, 2, 1].map(n => `<option value="${n}">${'★'.repeat(n)}</option>`).join('')}</select>
    <button class="btn ${saved ? '' : 'ghost'} small" data-act="bookmark" data-id="${r.id}">${saved ? '★ Saved' : '☆ Save'}</button></div></div></div>`;
}

/* ---------- Q&A ---------- */
let QAF = { q: '' };
function qa(param) { return param ? qaDetail(param) : qaList(); }
function qaList() {
  let list = S.questions.map(q => ({ q, sc: QAF.q ? searchScore(QAF.q, q.title + ' ' + q.body + ' ' + q.topic + ' ' + q.subject) : 1 }));
  if (QAF.q) list = list.filter(x => x.sc > 0);
  return head('Q&A Forum', 'Ask subject questions. Peers and seniors answer; faculty can verify the best answers.') + `
  <div class="grid g-main"><div class="stack">
    <form data-form="qaSearch" class="card row"><input name="q" value="${esc(QAF.q)}" placeholder="Search questions (e.g. noise, threads, joins)" style="flex:1"><button class="btn">Search</button></form>
    ${list.map(({ q }) => { const a = person(q.by), acc = q.answers.some(x => x.accepted), ver = q.answers.some(x => x.verified); return `<a href="#/qa/${q.id}" class="card" style="display:block;color:inherit"><div class="row between"><b>${esc(q.title)}</b><span class="row" style="gap:.3rem">${ver ? '<span class="badge ok">Faculty verified</span>' : ''}${acc ? '<span class="badge ok">Accepted</span>' : ''}<span class="badge ${q.answers.length ? '' : 'warn'}">${q.answers.length} answers</span></span></div><small>${esc(q.subject)} · ${esc(q.topic)} · ${esc(a ? a.name : '')} · ${esc(q.when)}</small></a>`; }).join('') || '<div class="card empty">No questions found.</div>'}
  </div>
  ${S.role === 'faculty' ? '<div class="card"><h2>Faculty tip</h2><p>Open an accepted answer and click <b>Verify</b> to mark it as faculty-verified.</p></div>' : `<div class="card"><h2>Ask a question</h2>
    <form data-form="ask" class="grid-f">
      <label class="f">Title<input name="title" id="askTitle" data-input="similar" required maxlength="120" autocomplete="off"></label>
      <div id="similar"></div>
      <label class="f">Subject<input name="subject" required maxlength="40" placeholder="e.g. Operating Systems"></label>
      <label class="f">Topic<input name="topic" required maxlength="40"></label>
      <label class="f">Details<textarea name="body" required maxlength="800"></textarea></label>
      <button class="btn">Post question</button></form></div>`}</div>`;
}

function similarHtml(text) {
  if (text.trim().length < 3) return '';
  const hits = S.questions.map(q => ({ q, s: searchScore(text, q.title + ' ' + q.topic) })).filter(x => x.s > 1).sort((a, b) => b.s - a.s).slice(0, 3);
  if (!hits.length) return '';
  return `<div class="callout warn"><b>Already asked?</b>${hits.map(h => `<div><a href="#/qa/${h.q.id}">${esc(h.q.title)}</a></div>`).join('')}</div>`;
}

function qaDetail(id) {
  const q = S.questions.find(x => x.id === id);
  if (!q) return '<div class="card empty">Question not found. <a href="#/qa">Back</a></div>';
  const a = person(q.by), isAsker = q.by === S.meId;
  const sorted = q.answers.slice().sort((x, y) => (y.accepted - x.accepted) || (y.votes - x.votes));
  return `<p><a href="#/qa">← All questions</a></p>
  <div class="card"><h1 style="font-size:1.3rem">${esc(q.title)}</h1><small>${esc(q.subject)} · ${esc(q.topic)} · asked by ${esc(a ? a.name : '')} · ${esc(q.when)}</small><p style="margin-top:.7rem">${esc(q.body)}</p></div>
  <h2 style="margin:1rem 0 .3rem">${q.answers.length} answer${q.answers.length === 1 ? '' : 's'}</h2>
  ${sorted.map(x => { const w = person(x.by); return `<div class="card"><div class="answer ${x.accepted ? 'accepted' : ''}" style="border:0;padding:0;margin:0"><div class="row between"><span class="row" style="gap:.5rem">${w ? avatar(w) : ''}<b>${esc(w ? w.name : '')}</b>${x.accepted ? '<span class="badge ok">Accepted</span>' : ''}${x.verified ? '<span class="badge ok">✔ Faculty verified</span>' : ''}</span>
    <span class="row"><button class="btn ghost small" data-act="vote" data-q="${q.id}" data-a="${x.id}">▲ ${x.votes}</button>${isAsker && !x.accepted ? `<button class="btn ok small" data-act="accept" data-q="${q.id}" data-a="${x.id}">Accept</button>` : ''}${S.role === 'faculty' && !x.verified ? `<button class="btn small" data-act="verifyAns" data-q="${q.id}" data-a="${x.id}">Verify</button>` : ''}</span></div>
    <p style="margin:.6rem 0 0">${esc(x.text)}</p></div></div>`; }).join('')}
  ${q.answers.length === 0 ? '<div class="card empty">No answers yet. Be the first to help.</div>' : ''}
  <div class="card"><h2>Your answer</h2><form data-form="answer" data-q="${q.id}" class="grid-f"><textarea name="text" required maxlength="1200" placeholder="Explain step by step. Examples help."></textarea><button class="btn">Post answer</button></form>
  <small>Accepted means useful to the asker. Faculty-verified is a stronger signal of correctness.</small></div>`;
}

/* ---------- Mentorship ---------- */
function mentors() { return S.role === 'senior' ? mentorInbox() : mentorDiscover(); }
function mentorDiscover() {
  const p = me();
  const gs = gapList(p, p.goal).filter(x => x.g > 0);
  const list = S.people.filter(x => x.role === 'senior').map(m => ({ m, ...mentorMatch(m, p) })).sort((a, b) => b.score - a.score);
  const mine = S.requests.filter(r => r.from === p.id).slice().reverse();
  return head('Senior–Junior Mentorship', 'Find seniors who have the skills you are missing and free time that matches yours.') + `
  <div class="callout">Your gaps for ${esc(p.goal)}: ${gs.map(x => `<span class="chip on">${esc(SHORT[x.k])} (${x.c}→${x.r})</span>`).join('') || 'none'}</div>
  <div class="grid g2" style="margin-top:1rem">${list.map(({ m, score, overlap, why }) => `
    <div class="card"><div class="row between"><div class="row">${avatar(m, 'lg')}<div><b>${esc(m.name)}</b><br><small>Year ${m.year} ${esc(m.branch)} · ★ ${m.rating} · ${m.mentees} mentees</small></div></div><div class="stat" style="text-align:right"><b>${Math.round(score * 100)}%</b><span>match</span></div></div>
      <div style="margin:.6rem 0">${Object.keys(m.skills).map(k => `<span class="chip ${why.includes(skillName(k)) ? 'on' : ''}">${esc(SHORT[k])} ${m.skills[k]}</span>`).join('')}</div>
      <small>${why.length ? 'Can help with: <b>' + why.map(esc).join(', ') + '</b>. ' : 'No direct skill match for your gaps. '}${overlap.length ? 'Shared free slots: <b>' + overlap.map(esc).join(', ') + '</b>.' : 'No shared free slots yet.'}</small>
      <details style="margin-top:.7rem"><summary class="btn small" style="display:inline-block;list-style:none">Request a session</summary>
        <form data-form="mentorReq" data-to="${m.id}" class="grid-f" style="margin-top:.7rem">
          <label class="f">Topic<select name="topic">${(gs.length ? gs.map(x => x.k) : Object.keys(m.skills)).map(k => `<option value="${k}">${esc(skillName(k))}</option>`).join('')}</select></label>
          <label class="f">Preferred slot<select name="slot">${(overlap.length ? overlap : m.avail).map(d => `<option>${esc(d)}</option>`).join('')}</select></label>
          <label class="f">Message<textarea name="msg" maxlength="300" placeholder="What do you want to get out of the session?"></textarea></label>
          <button class="btn">Send request</button></form></details></div>`).join('')}</div>
  <h2 style="margin:1.2rem 0 .5rem">My requests</h2>
  ${mine.length ? mine.map(r => { const m = person(r.to); return `<div class="card"><div class="row between"><div><b>${esc(skillName(r.topic))}</b> with ${esc(m.name)} <small>· ${esc(r.slot)}</small></div><span class="badge ${r.status === 'accepted' ? 'ok' : r.status === 'declined' ? 'bad' : 'warn'}">${esc(r.status)}</span></div>
    ${r.status === 'accepted' && r.post == null ? `<form data-form="prepost" data-rid="${r.id}" class="row" style="margin-top:.6rem;align-items:end"><label class="f">Pre-session score (0-10)<input type="number" name="pre" min="0" max="10" required></label><label class="f">Post-session score (0-10)<input type="number" name="post" min="0" max="10" required></label><button class="btn small">Log improvement</button></form>` : ''}
    ${r.post != null ? `<div class="callout ok" style="margin-top:.6rem">Improvement: ${r.pre}/10 → ${r.post}/10 (<b>${r.post - r.pre >= 0 ? '+' : ''}${r.post - r.pre}</b>)</div>` : ''}</div>`; }).join('') : '<div class="card empty">No requests yet.</div>'}`;
}

function mentorInbox() {
  const p = me();
  const inbox = S.requests.filter(r => r.to === p.id).slice().reverse();
  return head('Mentor Inbox', 'Respond to requests from juniors. Improvement is measured with before/after scores.') +
    (inbox.length ? inbox.map(r => { const f = person(r.from); return `<div class="card"><div class="row between"><div class="row">${avatar(f)}<div><b>${esc(f.name)}</b> asks about <b>${esc(skillName(r.topic))}</b><br><small>Slot: ${esc(r.slot)} · Year ${f.year} ${esc(f.branch)}</small></div></div><span class="badge ${r.status === 'accepted' ? 'ok' : r.status === 'declined' ? 'bad' : 'warn'}">${esc(r.status)}</span></div>
      ${r.msg ? `<p style="margin:.6rem 0 0">“${esc(r.msg)}”</p>` : ''}
      ${r.status === 'pending' ? `<div class="row" style="margin-top:.7rem"><button class="btn ok small" data-act="reqAccept" data-rid="${r.id}">Accept</button><button class="btn ghost small" data-act="reqDecline" data-rid="${r.id}">Decline</button></div>` : ''}
      ${r.post != null ? `<div class="callout ok" style="margin-top:.6rem">Mentee improved ${r.pre}/10 → ${r.post}/10</div>` : ''}</div>`; }).join('') :
      '<div class="card empty">No requests yet. Switch to the Student role, request a session from Priya, then come back here.</div>');
}

/* ---------- Projects & team matching ---------- */
function projects(param) { return param ? projectDetail(param) : projectList(); }
function projectList() {
  return head('Projects & Team Matcher', 'Post a project and get teammates ranked by complementary skills, experience, availability and interest.') + `
  <div class="grid g-main"><div class="stack">${S.projects.map(pr => { const o = person(pr.owner); return `<div class="card"><div class="row between"><div><b>${esc(pr.title)}</b><br><small>by ${esc(o.name)} · ${esc(pr.timeline)} · team of ${pr.size}</small></div><a class="btn small" href="#/projects/${pr.id}">${pr.owner === S.meId ? 'Find teammates' : 'View'}</a></div>
    <p style="margin:.5rem 0">${esc(pr.desc)}</p><div>${pr.needs.map(k => `<span class="chip on">${esc(SHORT[k])}</span>`).join('')}${pr.tags.map(t => `<span class="chip">${esc(t)}</span>`).join('')}</div>
    <small>Members: ${pr.members.map(m => esc(person(m).name)).join(', ')}</small></div>`; }).join('')}</div>
  <div class="card"><h2>Post a project</h2><form data-form="project" class="grid-f">
    <label class="f">Title<input name="title" required maxlength="80"></label>
    <label class="f">Description<textarea name="desc" required maxlength="400"></textarea></label>
    <label class="f">Skills needed (hold Ctrl/Cmd to pick several)<select name="needs" multiple size="6" required>${Object.keys(SKILLS).map(k => `<option value="${k}">${esc(SKILLS[k].n)}</option>`).join('')}</select></label>
    <label class="f">Interest tags (comma separated)<input name="tags" placeholder="AI, Web, Healthcare"></label>
    <div class="row"><label class="f">Team size<input type="number" name="size" min="2" max="6" value="3"></label><label class="f">Timeline<input name="timeline" value="6 weeks"></label></div>
    <button class="btn">Post project</button></form></div></div>`;
}

function projectDetail(id) {
  const pr = S.projects.find(x => x.id === id);
  if (!pr) return '<div class="card empty">Project not found. <a href="#/projects">Back</a></div>';
  const ranked = rankCandidates(pr), sug = suggestTeam(pr), owner = pr.owner === S.meId;
  const inv = uidv => pr.invites.find(i => i.uid === uidv);
  return `<p><a href="#/projects">← All projects</a></p>
  <div class="card"><h1 style="font-size:1.3rem">${esc(pr.title)}</h1><p>${esc(pr.desc)}</p><div>${pr.needs.map(k => `<span class="chip on">${esc(skillName(k))}</span>`).join('')}</div>
    ${!owner ? `<button class="btn" style="margin-top:.6rem" data-act="joinProject" data-id="${pr.id}" ${pr.invites.some(i => i.uid === S.meId) ? 'disabled' : ''}>${pr.invites.some(i => i.uid === S.meId) ? 'Request sent' : 'Request to join'}</button>` : ''}</div>
  <div class="grid g-main" style="margin-top:1rem"><div class="card"><h2>Ranked candidates</h2>
    <div class="callout" style="margin-bottom:.6rem">Score = 0.45·Skills + 0.20·Experience + 0.20·Availability + 0.15·Interest. These weights are starting values, not tuned.</div>
    <table class="table"><thead><tr><th>Candidate</th><th>Match</th><th class="hide-sm">Skills</th><th class="hide-sm">Exp.</th><th class="hide-sm">Avail.</th><th class="hide-sm">Interest</th><th></th></tr></thead><tbody>
    ${ranked.map(x => `<tr><td><b>${esc(x.c.name)}</b><br><small>${pr.needs.map(k => esc(SHORT[k]) + ' ' + (x.c.skills[k] || 0)).join(' · ')}</small></td><td><b>${Math.round(x.S * 100)}%</b></td><td class="hide-sm">${pct(x.K)}</td><td class="hide-sm">${pct(x.E)}</td><td class="hide-sm">${pct(x.A)}</td><td class="hide-sm">${pct(x.I)}</td>
      <td>${owner ? (inv(x.c.id) ? '<span class="badge ok">Invited</span>' : `<button class="btn small" data-act="invite" data-id="${pr.id}" data-u="${x.c.id}">Invite</button>`) : ''}</td></tr>`).join('')}
    </tbody></table></div>
  <div class="card"><h2>Suggested balanced team</h2><p><small>Chosen greedily to cover missing skills, not just the highest individual scores. Nobody is auto-assigned: invitations need approval.</small></p>
    ${sug.team.map(x => `<div class="row" style="margin:.4rem 0">${avatar(x.c)}<div><b>${esc(x.c.name)}</b><br><small>${Math.round(x.S * 100)}% match</small></div></div>`).join('') || '<small>No more slots.</small>'}
    <div style="margin-top:.6rem"><b>Coverage</b><br>${pr.needs.map(k => `<span class="chip ${sug.covered.includes(k) ? 'on' : ''}">${sug.covered.includes(k) ? '✔' : '✘'} ${esc(SHORT[k])}</span>`).join('')}</div>
    ${sug.missing.length ? `<div class="callout warn" style="margin-top:.6rem">Still missing: ${sug.missing.map(k => esc(skillName(k))).join(', ')}. Consider asking a senior mentor.</div>` : '<div class="callout ok" style="margin-top:.6rem">Every required skill is covered at level 3 or higher.</div>'}</div></div>`;
}

/* ---------- Project generator ---------- */
function ideas() {
  const p = me(), list = projectIdeas(p);
  return head('Personalized Project Generator', 'Project ideas matched to your current level and the skills you still need to prove.') +
    `<div class="grid g2">${list.map(({ idea, stretch, builds, fits }) => `<div class="card"><div class="row between"><b>${esc(idea.title)}</b><span class="badge ${fits ? 'ok' : 'warn'}">${fits ? idea.level : 'Stretch'}</span></div>
    <p style="margin:.4rem 0"><small>${esc(idea.outcome)}</small></p>
    <div>${Object.entries(idea.skills).map(([k, v]) => `<span class="chip ${(p.skills[k] || 0) >= v ? 'on' : ''}">${esc(SHORT[k])} ≥ ${v}</span>`).join('')}</div>
    ${builds.length ? `<small>Builds your gap skills: <b>${builds.map(k => esc(SHORT[k])).join(', ')}</b></small><br>` : ''}
    ${stretch.length ? `<small>You are below the level for: ${stretch.map(k => esc(SHORT[k])).join(', ')}. Expect to learn as you go.</small>` : '<small>You already meet every prerequisite.</small>'}
    <ol style="margin:.6rem 0 .6rem 1.1rem;padding:0">${idea.milestones.map(m => `<li>${esc(m)}</li>`).join('')}</ol>
    <button class="btn small" data-act="startIdea" data-t="${esc(idea.title)}">Add milestones to my planner</button></div>`).join('')}</div>`;
}

/* ---------- Internship readiness ---------- */
let RDY = { role: 'ML Engineer', jd: '' };
function readinessPage() {
  const p = me();
  const jdSkills = RDY.jd.trim() ? extractSkills(RDY.jd) : null;
  const req = jdSkills && Object.keys(jdSkills).length ? jdSkills : ROLES[RDY.role].req;
  const rd = readiness(p, req);
  const src = jdSkills ? (Object.keys(jdSkills).length ? 'your job description' : null) : null;
  const col = (state, title, cls) => { const rows = rd.rows.filter(r => r.state === state); return `<div class="card"><h2>${title} <span class="badge ${cls}">${rows.length}</span></h2>${rows.map(r => `<div class="row between" style="padding:.3rem 0"><span>${esc(skillName(r.k))}</span><span>${lvlBar(r.c, r.r)}</span></div>`).join('') || '<small>None</small>'}</div>`; };
  const missing = rd.rows.filter(r => r.state !== 'ok');
  const recs = missing.flatMap(r => S.resources.filter(x => x.skill === r.k).sort((a, b) => b.gain - a.gain).slice(0, 1));
  const idea = projectIdeas(p).find(x => x.builds.some(k => missing.some(m => m.k === k)));
  return head('Internship Readiness Analyzer', 'Compare your demonstrated skills with a role, or paste a job description.') + `
  <form data-form="readiness" class="card grid-f"><div class="row" style="align-items:end"><label class="f">Role template${roleSelect('role', RDY.role)}</label><span class="muted">or</span></div>
    <label class="f">Paste a job description (optional, overrides the template)<textarea name="jd" placeholder="Paste text from an internship posting...">${esc(RDY.jd)}</textarea></label>
    <div class="row"><button class="btn">Analyze</button>${!jdSkills ? `<button type="button" class="btn ghost" data-act="setGoal" data-r="${esc(RDY.role)}">Set as my target role</button>` : ''}</div></form>
  ${RDY.jd.trim() && !src ? '<div class="callout warn" style="margin-top:1rem">No known skills were found in that text, so the role template is used instead.</div>' : ''}
  ${jdSkills && src ? `<div class="callout" style="margin-top:1rem">Found ${Object.keys(jdSkills).length} skills in ${src} using keyword matching: ${Object.keys(jdSkills).map(k => `<span class="chip on">${esc(SHORT[k])}</span>`).join('')}. Required level is assumed to be 3.</div>` : ''}
  <div class="grid g4" style="margin-top:1rem"><div class="card row" style="grid-column:span 1"><div class="score-ring" style="--p:${rd.pct}"><b>${rd.pct}%</b></div></div>
    ${col('ok', 'Demonstrated', 'ok').replace('class="card"', 'class="card"')}${col('partial', 'Partial', 'warn')}${col('missing', 'Missing', 'bad')}</div>
  <div class="grid g2" style="margin-top:1rem"><div class="card"><h2>Close the gaps</h2>${recs.length ? recs.map(r => resourceMini(r)).join('') : '<div class="empty">Nothing to learn. You are ready.</div>'}</div>
  <div class="card"><h2>Project to prove it</h2>${idea ? `<b>${esc(idea.idea.title)}</b><p><small>${esc(idea.idea.outcome)}</small></p><a class="btn small" href="#/ideas">See milestones</a>` : '<div class="empty">No matching project idea.</div>'}</div></div>`;
}

/* ---------- Aptitude ---------- */
function aptitude() {
  const hist = S.quiz.history;
  if (!QZ) {
    const last = hist[hist.length - 1];
    return head('Adaptive Aptitude Prep', 'Difficulty moves up after a correct answer and down after a mistake.') + `
    <div class="grid g2"><div class="card"><h2>Start a mock</h2><p>8 questions across quantitative, probability, reasoning and verbal.</p><button class="btn" data-act="quizStart">Start adaptive mock</button></div>
    <div class="card"><h2>Your history</h2>${hist.length ? lineChart(hist.map(h => Math.round(100 * h.score / h.total)), hist.map((h, i) => '#' + (i + 1))) + (last ? `<small>Weakest topics last time: ${weakTopics(last.topics).slice(0, 2).map(w => esc(w.topic) + ' (' + pct(w.acc) + ')').join(', ')}</small>` : '') : '<div class="empty">No attempts yet.</div>'}</div></div>`;
  }
  if (QZ.done) {
    const wk = weakTopics(QZ.log);
    return head('Aptitude Results', '') + `<div class="grid g2"><div class="card row"><div class="score-ring" style="--p:${Math.round(100 * QZ.correct / QZ.log.length)}"><b>${QZ.correct}/${QZ.log.length}</b></div><div><b>${QZ.correct / QZ.log.length >= 0.7 ? 'Strong attempt' : 'Keep practising'}</b><p><small>Final difficulty level: ${QZ.lvl}/3</small></p></div></div>
    <div class="card"><h2>By topic</h2>${bars(wk.map(w => ({ label: w.topic, value: Math.round(w.acc * 100) })))}</div></div>
    <div class="card"><h2>Review</h2>${QZ.log.map((l, i) => { const q = APT.find(x => x.id === l.id); return `<div style="padding:.4rem 0;border-bottom:1px solid var(--line)"><span class="badge ${l.ok ? 'ok' : 'bad'}">${l.ok ? 'Correct' : 'Wrong'}</span> <b>${esc(q.q)}</b><br><small>${esc(q.e)}</small></div>`; }).join('')}</div>
    <div class="row" style="margin-top:1rem"><button class="btn" data-act="quizStart">Try again</button><button class="btn ghost" data-act="quizExit">Back</button></div>`;
  }
  const q = QZ.cur, n = QZ.asked.length;
  return head('Aptitude Mock', `Question ${n} of ${QZ.n} · <span class="badge">${esc(q.topic)}</span> <span class="badge grey">Level ${q.lvl}</span>`) + `
  <div class="card"><div class="bar" style="margin-bottom:1rem"><i style="width:${(n - 1) / QZ.n * 100}%"></i></div><h2>${esc(q.q)}</h2>
  ${q.o.map((o, i) => `<button class="q-opt ${QZ.picked === null ? '' : i === q.a ? 'right' : i === QZ.picked ? 'wrong' : ''}" data-act="quizAns" data-i="${i}" ${QZ.picked !== null ? 'disabled' : ''}>${esc(o)}</button>`).join('')}
  ${QZ.picked !== null ? `<div class="callout ${QZ.picked === q.a ? 'ok' : 'bad'}"><b>${QZ.picked === q.a ? 'Correct.' : 'Not quite.'}</b> ${esc(q.e)}</div><div style="margin-top:.8rem"><button class="btn" data-act="quizNext">${n >= QZ.n ? 'See results' : 'Next question'}</button></div>` : ''}</div>`;
}

/* ---------- Technical practice ---------- */
function technical() {
  const stats = S.tech.stats;
  if (TQ && !TQ.done) {
    const q = TQ.items[TQ.i];
    return head('Technical Practice', `Question ${TQ.i + 1} of ${TQ.items.length} · <span class="badge">${esc(q.topic)}</span>`) + `<div class="card"><h2>${esc(q.q)}</h2>
    ${q.o.map((o, i) => `<button class="q-opt ${TQ.picked === null ? '' : i === q.a ? 'right' : i === TQ.picked ? 'wrong' : ''}" data-act="techAns" data-i="${i}" ${TQ.picked !== null ? 'disabled' : ''}>${esc(o)}</button>`).join('')}
    ${TQ.picked !== null ? `<div class="callout ${TQ.picked === q.a ? 'ok' : 'bad'}"><b>${TQ.picked === q.a ? 'Correct.' : 'Not quite.'}</b> ${esc(q.e)}</div><div style="margin-top:.8rem"><button class="btn" data-act="techNext">${TQ.i + 1 >= TQ.items.length ? 'Finish' : 'Next'}</button></div>` : ''}</div>`;
  }
  const topics = [...new Set(TECH.map(t => t.skill))];
  const done = TQ && TQ.done;
  return head('Technical Interview Practice', 'Topic MCQs plus a curated coding list. Scoring 70%+ over 3 or more questions in a topic marks the skill as assessment-verified.') +
    (done ? `<div class="callout ok" style="margin-bottom:1rem">Finished: ${TQ.correct}/${TQ.items.length} correct. Your Skill Passport has been updated where thresholds were met.</div>` : '') + `
  <div class="grid g2"><div class="card"><h2>MCQ practice</h2><div class="row">${topics.map(t => `<button class="btn ghost small" data-act="techStart" data-t="${t}">${esc(skillName(t))}</button>`).join('')}<button class="btn small" data-act="techStart" data-t="all">All topics</button></div>
    <h3 style="margin-top:1rem">Your accuracy</h3>${Object.keys(stats).length ? bars(Object.entries(stats).map(([k, v]) => ({ label: skillName(k) + ' (' + v.a + ' attempted)', value: Math.round(100 * v.c / v.a) }))) : '<div class="empty">Answer a few questions to see accuracy.</div>'}</div>
  <div class="card"><h2>Coding practice list</h2><small>Solve on your preferred judge, then mark here. Code execution is not part of this front end.</small>
    ${CODING.map(c => `<div class="row between" style="padding:.45rem 0;border-bottom:1px solid var(--line)"><div><b>${esc(c.t)}</b><br><small>${esc(c.topic)}</small></div><span class="row"><span class="badge ${c.d === 'Easy' ? 'ok' : c.d === 'Medium' ? 'warn' : 'bad'}">${c.d}</span><button class="btn ${S.coding.includes(c.id) ? '' : 'ghost'} small" data-act="codeToggle" data-id="${c.id}">${S.coding.includes(c.id) ? '✔ Solved' : 'Mark solved'}</button></span></div>`).join('')}
    <small>${S.coding.length}/${CODING.length} solved</small></div></div>`;
}

/* ---------- Mock interview ---------- */
function interview() {
  if (!IV) {
    const h = S.interviews;
    return head('AI Mock Interviewer', 'Practice with role-style questions and get rubric feedback.') + `<div class="callout warn" style="margin-bottom:1rem"><b>Honest note:</b> this demo scores answers with a rule-based rubric (keyword coverage, length, use of examples). It is a practice aid, not a real AI judge. A connected language model can replace the scorer later.</div>
    <div class="grid g2"><div class="card"><h2>Start an interview</h2><div class="stack">${Object.keys(INTERVIEW).map(t => `<button class="btn ${t === 'Technical' ? '' : 'ghost'}" style="width:100%" data-act="ivStart" data-t="${t}">${esc(t)} interview (${INTERVIEW[t].length} questions)</button>`).join('')}</div></div>
    <div class="card"><h2>Progress</h2>${h.length ? lineChart(h.map(x => x.avg), h.map(x => x.type[0] + (h.indexOf(x) + 1))) : '<div class="empty">No interviews yet.</div>'}</div></div>`;
  }
  if (IV.done) {
    return head('Interview Summary', `${esc(IV.type)} interview`) + `<div class="card row"><div class="score-ring" style="--p:${IV.avg}"><b>${IV.avg}</b></div><div><b>${IV.avg >= 70 ? 'Solid performance' : IV.avg >= 45 ? 'Getting there' : 'Needs more practice'}</b><p><small>Average rubric score out of 100.</small></p></div></div>
    ${IV.res.map((r, i) => `<div class="card"><b>Q${i + 1}. ${esc(INTERVIEW[IV.type][i].q)}</b><p><small>Score ${r.score}/100 · ${r.words} words</small></p><div class="bar ${r.score >= 70 ? 'ok' : r.score >= 45 ? 'warn' : 'bad'}"><i style="width:${r.score}%"></i></div></div>`).join('')}
    <div class="row" style="margin-top:1rem"><button class="btn" data-act="ivStart" data-t="${esc(IV.type)}">Try again</button><button class="btn ghost" data-act="ivExit">Back</button></div>`;
  }
  const qs = INTERVIEW[IV.type], q = qs[IV.i], fb = IV.fb;
  return head(`${esc(IV.type)} Interview`, `Question ${IV.i + 1} of ${qs.length}`) + `<div class="card"><h2>${esc(q.q)}</h2>
  ${!fb ? `<form data-form="ivAnswer" class="grid-f"><textarea name="text" required placeholder="Type your answer as you would say it. Aim for 40+ words with an example." minlength="3"></textarea><button class="btn">Submit answer</button></form>` : `
  <div class="row"><div class="score-ring" style="--p:${fb.score};width:90px;height:90px"><b style="font-size:1.2rem">${fb.score}</b></div><div><b>${fb.score >= 70 ? 'Good answer' : fb.score >= 45 ? 'Decent, can improve' : 'Needs more depth'}</b><br><small>${fb.words} words</small></div></div>
  <div class="grid g3" style="margin-top:.8rem"><div><small>Coverage</small><div class="bar"><i style="width:${fb.cov * 100}%"></i></div></div><div><small>Completeness</small><div class="bar"><i style="width:${fb.len * 100}%"></i></div></div><div><small>Clarity / examples</small><div class="bar"><i style="width:${fb.clar * 100}%"></i></div></div></div>
  ${fb.hit.length ? `<p style="margin-top:.8rem"><small>Strong points mentioned:</small> ${fb.hit.map(h => `<span class="chip on">${esc(h)}</span>`).join('')}</p>` : ''}
  ${fb.missed.length ? `<p><small>Consider covering:</small> ${fb.missed.slice(0, 5).map(h => `<span class="chip">${esc(h)}</span>`).join('')}</p>` : ''}
  ${fb.words < 40 ? '<div class="callout warn">Your answer is short. Add a concrete example or result.</div>' : ''}
  <button class="btn" style="margin-top:.8rem" data-act="ivNext">${IV.i + 1 >= qs.length ? 'See summary' : 'Next question'}</button>`}</div>`;
}

/* ---------- Planner & groups ---------- */
function planner() {
  const p = me(), steps = pathway(p, p.goal).filter(s => s.state !== 'locked');
  const plan = p.avail.map((d, i) => ({ d, s: steps.length ? steps[i % steps.length] : null }));
  return head('Study Planner & Peer Groups', 'Turn your pathway into a weekly plan and study with others.') + `
  <div class="grid g2"><div class="stack">
    <div class="card"><h2>Weekly plan</h2><small>Built from your free slots and the current pathway steps.</small>
      ${plan.map(x => `<div class="row between" style="padding:.45rem 0;border-bottom:1px solid var(--line)"><b>${esc(x.d)}</b><span>${x.s ? esc(skillName(x.s.k)) + ' practice' : 'Free revision'}</span></div>`).join('')}</div>
    <div class="card"><h2>My tasks</h2>
      <form data-form="task" class="row" style="margin:.5rem 0"><input name="text" required maxlength="100" placeholder="Add a task" style="flex:1"><button class="btn">Add</button></form>
      ${S.tasks.map(t => `<div class="row between" style="padding:.35rem 0"><label class="row" style="gap:.5rem;cursor:pointer"><input type="checkbox" class="inline" style="width:auto" data-change="task" data-id="${t.id}" ${t.done ? 'checked' : ''}><span style="${t.done ? 'text-decoration:line-through;color:var(--muted)' : ''}">${esc(t.text)}</span></label><button class="btn ghost small" data-act="taskDel" data-id="${t.id}" aria-label="Delete task">✕</button></div>`).join('') || '<div class="empty">No tasks.</div>'}</div></div>
  <div class="card"><h2>Peer study groups</h2>${GROUPS.map(g => { const j = S.groups.includes(g.id); return `<div class="row between" style="padding:.6rem 0;border-bottom:1px solid var(--line)"><div><b>${esc(g.name)}</b><br><small>${esc(g.goal)} · ${g.members + (j ? 1 : 0)} members</small></div><button class="btn ${j ? '' : 'ghost'} small" data-act="group" data-id="${g.id}">${j ? 'Joined ✔' : 'Join'}</button></div>`; }).join('')}</div></div>`;
}

/* ---------- Faculty ---------- */
function faculty() {
  const open = S.questions.filter(q => q.answers.some(a => a.accepted && !a.verified));
  const eff = S.resources.slice().sort((a, b) => b.gain - a.gain).slice(0, 6);
  return head('Faculty Dashboard', 'Anonymized cohort insight. Individual grades are never shown to other students.') + `
  <div class="grid g4"><div class="card stat"><b>${S.people.filter(x => x.role === 'student').length * 14}</b><span>Active students (demo)</span></div>
    <div class="card stat"><b>${COHORT.atRisk.filter(x => x.risk === 'High').length}</b><span>High-risk cohorts</span></div>
    <div class="card stat"><b>${S.verify.length}</b><span>Skills awaiting verification</span></div>
    <div class="card stat"><b>${open.length}</b><span>Answers awaiting your review</span></div></div>
  <div class="grid g2" style="margin-top:1rem"><div class="card"><h2>Where students struggle</h2><small>% of attempts answered incorrectly (sample data)</small>${bars(COHORT.struggle, 'warn')}</div>
    <div class="card"><h2>At-risk signals</h2><table class="table"><thead><tr><th>Student</th><th>Subject</th><th>Trend</th><th>Risk</th></tr></thead><tbody>${COHORT.atRisk.map(x => `<tr><td>${esc(x.name)}</td><td>${esc(x.subject)}</td><td>${x.trend}%</td><td><span class="badge ${x.risk === 'High' ? 'bad' : 'warn'}">${x.risk}</span></td></tr>`).join('')}</tbody></table></div></div>
  <div class="grid g2" style="margin-top:1rem"><div class="card"><h2>Skill verification queue</h2>${S.verify.length ? S.verify.map((v, i) => { const u = person(v.uid); return `<div style="padding:.6rem 0;border-bottom:1px solid var(--line)"><b>${esc(u.name)}</b> · ${esc(skillName(v.skill))}<br><small>${esc(v.note)}</small><div class="row" style="margin-top:.4rem"><button class="btn ok small" data-act="verifyOk" data-i="${i}">Verify</button><button class="btn ghost small" data-act="verifyNo" data-i="${i}">Reject</button></div></div>`; }).join('') : '<div class="empty">Queue is empty.</div>'}</div>
  <div class="card"><h2>Resource effectiveness</h2><table class="table"><thead><tr><th>Resource</th><th>Users</th><th>Avg gain</th></tr></thead><tbody>${eff.map(r => `<tr><td>${esc(r.title)}</td><td>${r.users}</td><td><span class="badge ok">+${r.gain.toFixed(1)}</span></td></tr>`).join('')}</tbody></table>
    <h3 style="margin-top:1rem">Answers to review</h3>${open.map(q => `<div><a href="#/qa/${q.id}">${esc(q.title)}</a></div>`).join('') || '<small>All accepted answers are verified.</small>'}</div></div>`;
}

/* ---------- Login / sign-up (shown before the dashboard) ---------- */
let AUTH = { mode: 'login', err: '', busy: false };
function authPage() {
  const reg = AUTH.mode === 'register';
  const demo = [['student@alpg.demo', 'Student: Aarav Sharma'], ['mentor@alpg.demo', 'Senior mentor: Priya Verma'], ['faculty@alpg.demo', 'Faculty: Dr. S. Mehta']];
  return `<div class="auth-wrap">
  <section class="auth-hero"><div class="brand" style="padding:0"><span class="logo">A</span><div><b>ALPG</b><small>Adaptive Learning Pathway Generator</small></div></div>
    <h1>One platform to learn, connect and get career-ready.</h1>
    <p>Find what to learn next, learn from seniors, build projects with the right teammates, and prove your skills.</p>
    <ul><li>Prerequisite-aware learning pathway</li><li>Senior–junior mentorship and AI team matching</li><li>Skill Passport with verified evidence</li><li>Aptitude, technical and mock-interview prep</li></ul></section>
  <section class="auth-panel"><div class="auth-card">
    <h2>${reg ? 'Create your account' : 'Welcome back'}</h2>
    <p class="muted">${reg ? 'Students can sign up. Mentor and faculty accounts are created by admins.' : 'Sign in to continue to your dashboard.'}</p>
    ${AUTH.err ? `<div class="err" role="alert" style="margin:.6rem 0">${esc(AUTH.err)}</div>` : ''}
    ${reg ? `<form data-form="register" class="grid-f" novalidate>
      <label class="f">Full name<input name="name" autocomplete="name" required maxlength="60"></label>
      <label class="f">Email<input type="email" name="email" autocomplete="email" required></label>
      <div class="row" style="flex-wrap:nowrap"><label class="f" style="flex:1">Password<input type="password" name="pw" autocomplete="new-password" required minlength="8" placeholder="At least 8 characters"></label><label class="f" style="flex:1">Confirm<input type="password" name="pw2" autocomplete="new-password" required></label></div>
      <div class="row" style="flex-wrap:nowrap"><label class="f" style="flex:1">Year<select name="year"><option>1</option><option>2</option><option selected>3</option><option>4</option></select></label><label class="f" style="flex:1">Branch<select name="branch"><option>CSE</option><option>IT</option><option>ECE</option><option>Other</option></select></label></div>
      <label class="f">Target career<select name="goal">${Object.keys(ROLES).map(r => `<option>${esc(r)}</option>`).join('')}</select></label>
      <button class="btn" ${AUTH.busy ? 'disabled' : ''}>Create account</button></form>
      <p style="margin-top:1rem">Already registered? <a href="#/login" data-act="authMode" data-m="login">Sign in</a></p>` :
    `<form data-form="login" class="grid-f" novalidate>
      <label class="f">Email<input type="email" name="email" id="loginEmail" autocomplete="username" required></label>
      <label class="f">Password<input type="password" name="pw" id="loginPw" autocomplete="current-password" required></label>
      <button class="btn" ${AUTH.busy ? 'disabled' : ''}>Sign in</button></form>
      <p style="margin-top:1rem">New here? <a href="#/register" data-act="authMode" data-m="register">Create an account</a></p>
      <h3 style="margin-top:1.2rem">Demo accounts <small>(password: demo123)</small></h3>
      <div class="demo-accts">${demo.map(d => `<button type="button" data-act="fillDemo" data-e="${d[0]}">${esc(d[1])} <small>· ${esc(d[0])}</small></button>`).join('')}</div>`}
    <p class="pw-note" style="margin-top:1rem" id="serverNote">${API.online ? '🟢 Connected to the ALPG server: accounts are checked and stored there.' : '⚪ Offline demo mode: no server found, so sign-in is checked in this browser only.'} Do not reuse a real password.</p>
  </div></section></div>`;
}

const pages = {
  dashboard, passport, pathway: pathwayPage, resources, planner, qa, mentors, projects, ideas,
  readiness: readinessPage, aptitude, technical, interview, faculty,
};
