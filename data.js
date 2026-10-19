/* ALPG demo data. Everything here is mock data stored in the browser. */

const SKILLS = {
  python: { n: 'Python', pre: [], kw: ['python'] },
  dsa:    { n: 'Data Structures & Algorithms', pre: ['python'], kw: ['data structure', 'data structures', 'algorithm', 'algorithms', 'dsa', 'leetcode'] },
  oop:    { n: 'Object-Oriented Programming', pre: ['python'], kw: ['oop', 'object-oriented', 'object oriented', 'java', 'c++'] },
  sql:    { n: 'SQL', pre: [], kw: ['sql', 'mysql', 'postgres', 'postgresql', 'queries'] },
  dbms:   { n: 'DBMS', pre: ['sql'], kw: ['dbms', 'database', 'databases', 'normalization', 'transactions'] },
  os:     { n: 'Operating Systems', pre: [], kw: ['operating system', 'operating systems', 'scheduling', 'threads'] },
  net:    { n: 'Computer Networks', pre: [], kw: ['network', 'networks', 'networking', 'tcp', 'http', 'dns'] },
  git:    { n: 'Git & GitHub', pre: [], kw: ['git', 'github', 'version control'] },
  web:    { n: 'Web Fundamentals', pre: [], kw: ['html', 'css', 'javascript', 'frontend', 'front-end', 'web development'] },
  react:  { n: 'React', pre: ['web'], kw: ['react', 'reactjs', 'tailwind', 'redux'] },
  stats:  { n: 'Statistics', pre: [], kw: ['statistics', 'statistical', 'probability', 'hypothesis testing'] },
  ml:     { n: 'Machine Learning', pre: ['python', 'stats'], kw: ['machine learning', 'ml', 'scikit-learn', 'sklearn', 'pytorch', 'tensorflow', 'model training'] },
  comm:   { n: 'Communication', pre: [], kw: ['communication', 'presentation', 'teamwork', 'collaboration', 'stakeholder'] },
};

const ROLES = {
  'ML Engineer': {
    desc: 'Build and ship machine-learning models.',
    req: { python: 4, stats: 3, ml: 4, dsa: 3, git: 2 },
  },
  'Full-Stack Developer': {
    desc: 'Build complete web applications, front to back.',
    req: { web: 4, react: 3, sql: 3, git: 3, dsa: 3 },
  },
  'Software Developer (SDE)': {
    desc: 'Core software engineering and campus placement track.',
    req: { dsa: 4, oop: 4, dbms: 3, os: 3, python: 3, comm: 3 },
  },
  'Data Analyst': {
    desc: 'Turn data into decisions with SQL, Python and statistics.',
    req: { sql: 4, python: 3, stats: 3, comm: 3 },
  },
};

const DAYS = ['Mon eve', 'Tue eve', 'Wed eve', 'Thu eve', 'Fri eve', 'Sat morn', 'Sun eve'];

const PEOPLE = [
  { id: 'u1', name: 'Aarav Sharma', role: 'student', year: 3, branch: 'CSE', goal: 'ML Engineer', cgpa: 8.1,
    skills: { python: 3, dsa: 2, sql: 2, stats: 1, git: 2, web: 2, comm: 3, oop: 2 },
    status: { python: 'assessed', dsa: 'self', sql: 'self', stats: 'self', git: 'self', web: 'self', comm: 'self', oop: 'self' },
    interests: ['AI', 'Healthcare', 'Data'], avail: ['Mon eve', 'Wed eve', 'Sat morn'], projects: 1, rep: 35,
    learn: { style: 'Visual' },
    grades: [{ s: 'Data Structures', g: 74 }, { s: 'DBMS', g: 81 }, { s: 'Probability & Stats', g: 58 }, { s: 'Operating Systems', g: 69 }, { s: 'Python Programming', g: 88 }] },
  { id: 'u2', name: 'Priya Verma', role: 'senior', year: 4, branch: 'CSE', goal: 'ML Engineer', rating: 4.8, mentees: 6,
    skills: { python: 5, ml: 4, stats: 4, dsa: 4, git: 4, comm: 4 },
    status: { python: 'faculty', ml: 'assessed', stats: 'assessed', dsa: 'assessed', git: 'faculty', comm: 'self' },
    interests: ['AI', 'Healthcare'], avail: ['Wed eve', 'Sat morn', 'Sun eve'], projects: 5, rep: 210 },
  { id: 'u3', name: 'Rohan Gupta', role: 'senior', year: 4, branch: 'CSE', goal: 'Software Developer (SDE)', rating: 4.6, mentees: 9,
    skills: { dsa: 5, oop: 4, dbms: 4, os: 4, python: 4, comm: 4 },
    status: { dsa: 'faculty', oop: 'assessed', dbms: 'assessed', os: 'assessed', python: 'assessed', comm: 'self' },
    interests: ['Systems', 'Competitive'], avail: ['Mon eve', 'Fri eve'], projects: 4, rep: 175 },
  { id: 'u4', name: 'Ananya Iyer', role: 'senior', year: 4, branch: 'IT', goal: 'Full-Stack Developer', rating: 4.7, mentees: 5,
    skills: { web: 5, react: 5, sql: 4, git: 5, python: 3 },
    status: { web: 'faculty', react: 'assessed', sql: 'assessed', git: 'faculty', python: 'self' },
    interests: ['Web', 'Healthcare'], avail: ['Tue eve', 'Sat morn'], projects: 6, rep: 190 },
  { id: 'u5', name: 'Neha Singh', role: 'student', year: 3, branch: 'CSE', goal: 'Full-Stack Developer',
    skills: { python: 2, web: 4, react: 3, ml: 1, sql: 2, git: 3 }, status: {},
    interests: ['AI', 'Web'], avail: ['Mon eve', 'Wed eve'], projects: 2, rep: 40 },
  { id: 'u6', name: 'Karan Mehta', role: 'student', year: 3, branch: 'CSE', goal: 'ML Engineer',
    skills: { python: 4, ml: 3, stats: 3, dsa: 3, git: 3 }, status: {},
    interests: ['AI', 'Data'], avail: ['Wed eve', 'Sun eve'], projects: 3, rep: 65 },
  { id: 'u7', name: 'Ishita Rao', role: 'student', year: 2, branch: 'IT', goal: 'Data Analyst',
    skills: { web: 3, react: 2, sql: 3, comm: 4, stats: 2 }, status: {},
    interests: ['Web', 'Healthcare', 'Data'], avail: ['Mon eve', 'Sat morn'], projects: 1, rep: 22 },
  { id: 'u8', name: 'Vikram Patel', role: 'student', year: 3, branch: 'CSE', goal: 'Software Developer (SDE)',
    skills: { dsa: 4, oop: 3, python: 3, sql: 3 }, status: {},
    interests: ['Systems', 'AI'], avail: ['Tue eve', 'Wed eve'], projects: 2, rep: 48 },
  { id: 'f1', name: 'Dr. S. Mehta', role: 'faculty', branch: 'CSE', skills: {}, status: {}, interests: [], avail: [], rep: 0 },
];

const RESOURCES = [
  { id: 'r1', title: 'Python for ML: 2-hour crash course', type: 'Video', skill: 'python', topic: 'Python basics', by: 'u2', style: 'Visual', rating: 4.7, votes: 38, users: 22, gain: 2.6 },
  { id: 'r2', title: 'Statistics cheat-sheet: distributions & hypothesis tests', type: 'Notes', skill: 'stats', topic: 'Probability', by: 'u2', style: 'Read/Write', rating: 4.5, votes: 29, users: 17, gain: 3.1 },
  { id: 'r3', title: 'Scikit-learn workflow notebook', type: 'Practice', skill: 'ml', topic: 'Model training', by: 'u2', style: 'Kinesthetic', rating: 4.6, votes: 21, users: 11, gain: 2.2 },
  { id: 'r4', title: 'DSA patterns: arrays, two pointers, sliding window', type: 'Notes', skill: 'dsa', topic: 'Arrays', by: 'u3', style: 'Read/Write', rating: 4.8, votes: 56, users: 41, gain: 2.9 },
  { id: 'r5', title: 'Binary trees visualised', type: 'Video', skill: 'dsa', topic: 'Trees', by: 'u3', style: 'Visual', rating: 4.4, votes: 33, users: 27, gain: 1.8 },
  { id: 'r6', title: 'DBMS normalization: solved examples', type: 'Notes', skill: 'dbms', topic: 'Normalization', by: 'u3', style: 'Read/Write', rating: 4.3, votes: 19, users: 14, gain: 1.4 },
  { id: 'r7', title: 'OS scheduling algorithms: worked problems', type: 'Practice', skill: 'os', topic: 'CPU scheduling', by: 'u3', style: 'Kinesthetic', rating: 4.5, votes: 24, users: 18, gain: 2.4 },
  { id: 'r8', title: 'React from zero: components, props, state', type: 'Video', skill: 'react', topic: 'React basics', by: 'u4', style: 'Visual', rating: 4.7, votes: 44, users: 25, gain: 2.5 },
  { id: 'r9', title: 'SQL joins practice set (40 queries)', type: 'Practice', skill: 'sql', topic: 'Joins', by: 'u4', style: 'Kinesthetic', rating: 4.6, votes: 31, users: 29, gain: 3.3 },
  { id: 'r10', title: 'Git & GitHub in one afternoon', type: 'Article', skill: 'git', topic: 'Version control', by: 'u4', style: 'Read/Write', rating: 4.2, votes: 17, users: 20, gain: 1.1 },
  { id: 'r11', title: 'Image processing: spatial filters, solved', type: 'Notes', skill: 'python', topic: 'Median filter', by: 'u2', style: 'Read/Write', rating: 4.4, votes: 15, users: 9, gain: 2.0 },
  { id: 'r12', title: 'Probability past papers with solutions', type: 'Practice', skill: 'stats', topic: 'Probability', by: 'f1', style: 'Read/Write', rating: 4.9, votes: 62, users: 48, gain: 3.6 },
  { id: 'r13', title: 'Communication skills: explaining your project in 2 minutes', type: 'Article', skill: 'comm', topic: 'Interviews', by: 'u4', style: 'Read/Write', rating: 4.1, votes: 12, users: 13, gain: 1.5 },
  { id: 'r14', title: 'Computer networks: TCP/IP in diagrams', type: 'Video', skill: 'net', topic: 'TCP/IP', by: 'u3', style: 'Visual', rating: 4.3, votes: 16, users: 10, gain: 1.7 },
];

const QUESTIONS = [
  { id: 'q1', title: 'How do we apply a median filter to a 3×3 matrix?', body: 'I get the idea of sorting neighbours but I am not sure what happens at the borders.',
    subject: 'Image Processing', topic: 'Spatial filters', by: 'u5', when: '2 days ago', answers: [
      { id: 'a1', by: 'u2', text: 'Collect the 9 values in the window, sort them and take the middle one (the 5th). Replace the centre pixel with it. At borders, pad the image by replicating edge pixels, or skip border pixels.', votes: 7, accepted: true, verified: true },
      { id: 'a2', by: 'u6', text: 'Same as the averaging filter but you use the median instead of the mean, which is why it removes salt-and-pepper noise well.', votes: 3, accepted: false, verified: false },
    ] },
  { id: 'q2', title: 'Difference between a process and a thread?', body: 'Interview question I keep fumbling.',
    subject: 'Operating Systems', topic: 'Processes', by: 'u7', when: '1 day ago', answers: [
      { id: 'a3', by: 'u3', text: 'A process has its own address space; threads inside a process share code, heap and open files but each has its own stack and registers. Thread switches are cheaper than process switches.', votes: 5, accepted: false, verified: false },
    ] },
  { id: 'q3', title: 'When should I use a LEFT JOIN instead of INNER JOIN?', body: 'I keep losing rows from my result.',
    subject: 'DBMS', topic: 'Joins', by: 'u1', when: '5 hours ago', answers: [] },
  { id: 'q4', title: 'Probability: two dice, P(sum is 8 given at least one is a 6)?', body: 'Stuck on conditional probability here.',
    subject: 'Probability & Stats', topic: 'Conditional probability', by: 'u1', when: '1 hour ago', answers: [] },
];

const PROJECTS = [
  { id: 'p1', title: 'Campus Health Chatbot', desc: 'A chatbot that answers student health-centre queries and books slots.', owner: 'u5',
    needs: ['python', 'ml', 'web'], tags: ['AI', 'Healthcare'], size: 4, timeline: '8 weeks', members: ['u5'], invites: [] },
  { id: 'p2', title: 'Placement Tracker Dashboard', desc: 'Dashboard that tracks applications, deadlines and interview rounds.', owner: 'u7',
    needs: ['react', 'sql', 'web'], tags: ['Web', 'Data'], size: 3, timeline: '6 weeks', members: ['u7'], invites: [] },
];

const APT = [
  { id: 'a1', topic: 'Percentages', lvl: 1, q: 'What is 20% of 250?', o: ['25', '40', '50', '55'], a: 2, e: '20% = 1/5, and 250 / 5 = 50.' },
  { id: 'a2', topic: 'Ratios', lvl: 1, q: 'If A:B = 2:3 and B = 18, what is A?', o: ['9', '12', '15', '27'], a: 1, e: 'B is 3 parts = 18, so one part = 6 and A = 2 × 6 = 12.' },
  { id: 'a3', topic: 'Percentages', lvl: 2, q: 'A price rises 20% then falls 20%. Net change?', o: ['No change', '4% decrease', '4% increase', '2% decrease'], a: 1, e: '1.2 × 0.8 = 0.96, a 4% decrease.' },
  { id: 'a4', topic: 'Time & Work', lvl: 2, q: 'A finishes a job in 10 days, B in 15 days. Together?', o: ['5 days', '6 days', '8 days', '12.5 days'], a: 1, e: 'Rates add: 1/10 + 1/15 = 1/6, so 6 days.' },
  { id: 'a5', topic: 'Probability', lvl: 2, q: 'Probability of getting a sum of 7 with two fair dice?', o: ['1/6', '1/12', '5/36', '7/36'], a: 0, e: '6 favourable outcomes out of 36 = 1/6.' },
  { id: 'a6', topic: 'Logical Reasoning', lvl: 2, q: 'Series: 2, 6, 12, 20, 30, ?', o: ['40', '42', '44', '36'], a: 1, e: 'Differences are 4, 6, 8, 10, so the next is +12 = 42.' },
  { id: 'a7', topic: 'Time & Work', lvl: 3, q: 'A can do a job in 12 days, B in 18. They work together for 4 days, then A leaves. How many more days does B need?', o: ['4', '6', '8', '10'], a: 1, e: 'Done in 4 days = 4 × (1/12 + 1/18) = 4 × 5/36 = 5/9. Remaining 4/9 at 1/18 per day = 8 days.' },
  { id: 'a8', topic: 'Probability', lvl: 3, q: 'Two cards drawn without replacement from 52. P(both are aces)?', o: ['1/169', '1/221', '1/13', '4/663'], a: 1, e: '(4/52) × (3/51) = 12/2652 = 1/221.' },
  { id: 'a9', topic: 'Logical Reasoning', lvl: 3, q: 'All A are B. Some B are C. Which must be true?', o: ['Some A are C', 'All C are A', 'No definite conclusion about A and C', 'No A is C'], a: 2, e: 'The overlap of B and C may not include any A, so nothing definite follows.' },
  { id: 'a10', topic: 'Verbal', lvl: 1, q: 'Choose the correct word: "The committee ___ its decision yesterday."', o: ['announce', 'announced', 'announcing', 'announces'], a: 1, e: '"Yesterday" signals the simple past: announced.' },
  { id: 'a11', topic: 'Ratios', lvl: 3, q: 'Mixture of milk and water is 5:3. How much water must be added to 16 L of mixture to make the ratio 5:4?', o: ['1 L', '2 L', '3 L', '4 L'], a: 1, e: '16 L has 10 L milk and 6 L water. For 5:4 water must be 8 L, so add 2 L.' },
  { id: 'a12', topic: 'Verbal', lvl: 2, q: 'Closest meaning of "ephemeral":', o: ['Lasting', 'Short-lived', 'Ancient', 'Harmful'], a: 1, e: 'Ephemeral means lasting for a very short time.' },
];

const TECH = [
  { id: 't1', skill: 'dsa', topic: 'DSA', q: 'Time complexity of binary search on a sorted array of n items?', o: ['O(n)', 'O(log n)', 'O(n log n)', 'O(1)'], a: 1, e: 'Each step halves the search space, giving O(log n).' },
  { id: 't2', skill: 'dsa', topic: 'DSA', q: 'Which structure gives O(1) average insert and lookup by key?', o: ['Linked list', 'Binary heap', 'Hash table', 'Sorted array'], a: 2, e: 'A hash table gives O(1) average-case insert and lookup.' },
  { id: 't3', skill: 'dsa', topic: 'DSA', q: 'Which traversal of a BST visits keys in sorted order?', o: ['Pre-order', 'In-order', 'Post-order', 'Level-order'], a: 1, e: 'In-order (left, node, right) visits BST keys in ascending order.' },
  { id: 't4', skill: 'dbms', topic: 'DBMS', q: 'Which normal form removes partial dependencies on a composite key?', o: ['1NF', '2NF', '3NF', 'BCNF'], a: 1, e: '2NF removes partial dependency of non-key attributes on part of a composite key.' },
  { id: 't5', skill: 'dbms', topic: 'DBMS', q: 'In ACID, what does the "I" stand for?', o: ['Integrity', 'Isolation', 'Indexing', 'Inheritance'], a: 1, e: 'Isolation: concurrent transactions do not see each other\'s partial results.' },
  { id: 't6', skill: 'sql', topic: 'SQL', q: 'Which join keeps all rows from the left table even with no match?', o: ['INNER JOIN', 'LEFT JOIN', 'CROSS JOIN', 'SELF JOIN'], a: 1, e: 'LEFT JOIN keeps every left row and fills unmatched right columns with NULL.' },
  { id: 't7', skill: 'os', topic: 'OS', q: 'Which scheduling algorithm can cause starvation of long jobs?', o: ['Round Robin', 'FCFS', 'Shortest Job First', 'None of these'], a: 2, e: 'SJF keeps favouring short jobs, so long jobs may wait indefinitely.' },
  { id: 't8', skill: 'os', topic: 'OS', q: 'A deadlock requires which of these conditions?', o: ['Only mutual exclusion', 'Mutual exclusion, hold and wait, no pre-emption, circular wait', 'Only circular wait', 'Pre-emption and starvation'], a: 1, e: 'All four Coffman conditions must hold together.' },
  { id: 't9', skill: 'oop', topic: 'OOP', q: 'Which principle lets a subclass be used where its parent is expected?', o: ['Encapsulation', 'Polymorphism', 'Abstraction', 'Composition'], a: 1, e: 'Polymorphism (subtyping) lets a child object stand in for its parent type.' },
  { id: 't10', skill: 'net', topic: 'Networks', q: 'Which protocol provides reliable, ordered delivery?', o: ['UDP', 'IP', 'TCP', 'ICMP'], a: 2, e: 'TCP provides reliability through acknowledgements and retransmission.' },
  { id: 't11', skill: 'sql', topic: 'SQL', q: 'Which clause filters groups after GROUP BY?', o: ['WHERE', 'HAVING', 'ORDER BY', 'LIMIT'], a: 1, e: 'HAVING filters aggregated groups; WHERE filters rows before grouping.' },
  { id: 't12', skill: 'oop', topic: 'OOP', q: 'What does encapsulation primarily achieve?', o: ['Faster code', 'Hiding internal state behind an interface', 'Multiple inheritance', 'Memory cleanup'], a: 1, e: 'It bundles data with methods and hides internals behind a public interface.' },
];

const INTERVIEW = {
  'Technical': [
    { q: 'Explain the difference between a stack and a queue, with a real example of each.', kw: ['lifo', 'fifo', 'push', 'pop', 'enqueue', 'dequeue', 'undo', 'browser', 'print'] },
    { q: 'What is the time complexity of searching in a hash table, and what can make it worse?', kw: ['o(1)', 'average', 'collision', 'o(n)', 'hash function', 'load factor', 'chaining'] },
    { q: 'What is overfitting and how do you reduce it?', kw: ['training', 'validation', 'generalize', 'regularization', 'cross-validation', 'more data', 'dropout', 'simpler'] },
    { q: 'Explain how an index speeds up a database query, and its cost.', kw: ['b-tree', 'index', 'lookup', 'scan', 'write', 'storage', 'slower inserts', 'lookup'] },
  ],
  'HR': [
    { q: 'Tell me about yourself.', kw: ['background', 'project', 'skills', 'interest', 'goal', 'learn', 'internship', 'team'] },
    { q: 'Describe a time you worked in a team and faced a conflict.', kw: ['situation', 'task', 'action', 'result', 'communicat', 'listen', 'resolved', 'learned'] },
    { q: 'What is your biggest weakness?', kw: ['weakness', 'improving', 'working on', 'feedback', 'example', 'progress', 'learned'] },
    { q: 'Where do you see yourself in five years?', kw: ['grow', 'learn', 'role', 'contribute', 'lead', 'skills', 'company'] },
  ],
  'Project': [
    { q: 'Describe your most significant project in two minutes.', kw: ['problem', 'solution', 'tech', 'my role', 'result', 'challenge', 'users', 'learned'] },
    { q: 'What was the hardest technical problem you faced in it, and how did you solve it?', kw: ['problem', 'debug', 'tried', 'solution', 'because', 'tested', 'result'] },
    { q: 'If you had more time, what would you improve?', kw: ['improve', 'scale', 'test', 'performance', 'feature', 'security', 'user feedback'] },
    { q: 'How did you split work among teammates?', kw: ['role', 'responsib', 'git', 'review', 'meeting', 'task', 'deadline'] },
  ],
};

const PROJECT_IDEAS = [
  { title: 'Student Marks Predictor', level: 'Beginner', skills: { python: 2, stats: 1 }, milestones: ['Collect or simulate a marks dataset', 'Explore with pandas and plots', 'Fit a simple linear regression', 'Report error and write up'], outcome: 'Demonstrates Python + basic statistics.' },
  { title: 'Spam Message Classifier', level: 'Intermediate', skills: { python: 3, ml: 2, stats: 2 }, milestones: ['Clean a text dataset', 'Build TF-IDF features', 'Train and compare two classifiers', 'Evaluate with precision and recall'], outcome: 'Demonstrates end-to-end ML workflow.' },
  { title: 'Expense Tracker with Charts', level: 'Beginner', skills: { web: 2, git: 1 }, milestones: ['Design the UI', 'Store entries in localStorage', 'Add monthly chart', 'Publish on GitHub Pages'], outcome: 'Demonstrates web basics and Git.' },
  { title: 'Library Management with SQL', level: 'Beginner', skills: { sql: 2, dbms: 1 }, milestones: ['Design ER diagram', 'Create normalized tables', 'Write 15 queries incl. joins', 'Add indexes and compare timing'], outcome: 'Demonstrates SQL and DBMS design.' },
  { title: 'Algorithm Visualizer', level: 'Intermediate', skills: { dsa: 3, web: 2 }, milestones: ['Implement sorting algorithms', 'Animate steps in the browser', 'Add search and graph algorithms', 'Write complexity notes'], outcome: 'Demonstrates DSA with a visible product.' },
  { title: 'Full-Stack Notes Sharing App', level: 'Advanced', skills: { react: 3, sql: 3, web: 3, git: 3 }, milestones: ['Design schema and API', 'Build React front end', 'Add auth and uploads', 'Deploy and write tests'], outcome: 'Demonstrates full-stack delivery.' },
  { title: 'Mini Process Scheduler Simulator', level: 'Intermediate', skills: { os: 2, oop: 2, python: 2 }, milestones: ['Model processes', 'Implement FCFS, SJF, RR', 'Compute waiting times', 'Plot a Gantt chart'], outcome: 'Demonstrates OS concepts in code.' },
  { title: 'Image Denoising Toolkit', level: 'Intermediate', skills: { python: 3, stats: 1 }, milestones: ['Add noise to images', 'Implement mean and median filters', 'Compare PSNR', 'Package as a CLI'], outcome: 'Demonstrates Python and image processing.' },
];

const GROUPS = [
  { id: 'g1', name: 'DSA Daily', goal: 'Solve one DSA problem a day', members: 14, skill: 'dsa' },
  { id: 'g2', name: 'ML Study Circle', goal: 'Weekly ML paper and notebook reading', members: 9, skill: 'ml' },
  { id: 'g3', name: 'Placement Aptitude Squad', goal: 'Timed aptitude mocks every Sunday', members: 21, skill: 'comm' },
  { id: 'g4', name: 'Web Builders', goal: 'Build and review small web projects', members: 11, skill: 'web' },
];

const COHORT = {
  atRisk: [
    { name: 'Student A', subject: 'Data Structures', trend: -12, risk: 'High' },
    { name: 'Student B', subject: 'Probability & Stats', trend: -9, risk: 'High' },
    { name: 'Student C', subject: 'DBMS', trend: -6, risk: 'Medium' },
    { name: 'Student D', subject: 'Operating Systems', trend: -5, risk: 'Medium' },
    { name: 'Student E', subject: 'Probability & Stats', trend: -4, risk: 'Medium' },
  ],
  struggle: [
    { label: 'Probability & Stats', value: 62 },
    { label: 'Operating Systems', value: 48 },
    { label: 'Data Structures', value: 41 },
    { label: 'DBMS', value: 33 },
    { label: 'Computer Networks', value: 27 },
  ],
  pendingVerify: [
    { uid: 'u2', skill: 'ml', note: 'Completed Titanic classifier and scikit-learn assessment' },
    { uid: 'u4', skill: 'react', note: 'Shipped a React portfolio (GitHub link attached)' },
  ],
};

const SEED = {
  role: 'student',
  meId: 'u1',
  people: PEOPLE,
  resources: RESOURCES,
  questions: QUESTIONS,
  projects: PROJECTS,
  bookmarks: ['r4'],
  ratings: {},
  requests: [],
  quiz: { history: [] },
  tech: { stats: {} },
  interviews: [],
  tasks: [{ id: 'tk1', text: 'Revise conditional probability', done: false }, { id: 'tk2', text: 'Solve 3 DSA array problems', done: true }],
  groups: ['g1'],
  streak: { days: 4, last: '' },
  verify: COHORT.pendingVerify.map(x => Object.assign({}, x)),
  coding: [],
  session: null,
  accounts: [
    { email: 'student@alpg.demo', pw: 'demo123', uid: 'u1' },
    { email: 'mentor@alpg.demo', pw: 'demo123', uid: 'u2' },
    { email: 'faculty@alpg.demo', pw: 'demo123', uid: 'f1' },
  ],
  users: {},
  version: 2,
};

/* Per-user data (everything a person does that should not leak to another account). */
const PERSONAL = ['bookmarks', 'ratings', 'quiz', 'tech', 'interviews', 'tasks', 'groups', 'streak', 'coding'];
PERSONAL.forEach(k => { (SEED.users.u1 = SEED.users.u1 || {})[k] = JSON.parse(JSON.stringify(SEED[k])); });
