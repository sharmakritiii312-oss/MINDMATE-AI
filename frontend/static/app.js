/**
 * MindMate AI — Complete Frontend SPA v3
 * Beautiful dashboard + 10 fully functional pages
 */

const API = window.location.origin;
const USER_ID = 'default';

// ── State ─────────────────────────────────────────────────────────────────────
let chatSessionId = null;
let chatLoading   = false;
let mlReady       = false;

// ── DOM ───────────────────────────────────────────────────────────────────────
const nav       = document.getElementById('nav');
const content   = document.getElementById('content');
const pageTitle = document.getElementById('pageTitle');
const connDot   = document.getElementById('connDot');
const connText  = document.getElementById('connText');
const aiDot     = document.getElementById('aiDot');
const aiText    = document.getElementById('aiText');

// ── Toast ─────────────────────────────────────────────────────────────────────
let _toastWrap;
function toast(msg, type = 'success') {
  if (!_toastWrap) { _toastWrap = document.createElement('div'); _toastWrap.className = 'toast-wrap'; document.body.appendChild(_toastWrap); }
  const t = document.createElement('div'); t.className = `toast ${type}`; t.textContent = msg;
  _toastWrap.appendChild(t); setTimeout(() => t.remove(), 3200);
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}, timeoutMs = 15000) {
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: ctrl.signal,
      ...opts,
    });
    clearTimeout(tid);
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `HTTP ${res.status}`); }
    return res.json();
  } catch(e) {
    clearTimeout(tid);
    if (e.name === 'AbortError') throw new Error('Request timed out. Check the server is running.');
    throw e;
  }
}
const apiGet  = p => apiFetch(p);
const apiPost = (p, b) => apiFetch(p, { method: 'POST', body: JSON.stringify(b) });

// ── Health polling ────────────────────────────────────────────────────────────
async function pollHealth() {
  try {
    const h = await apiGet('/health');
    connDot.className = 'conn-dot on'; connText.textContent = 'Connected';
    if (h.ml_ready) {
      mlReady = true;
      aiDot.className = 'ai-dot ready'; aiText.textContent = 'AI Ready';
    } else {
      aiDot.className = 'ai-dot loading'; aiText.textContent = 'AI Loading…';
    }
  } catch {
    connDot.className = 'conn-dot err'; connText.textContent = 'Offline';
    aiDot.className = 'ai-dot err'; aiText.textContent = 'Offline';
  }
}

// ── Nav ───────────────────────────────────────────────────────────────────────
document.getElementById('menuBtn').addEventListener('click', () => nav.classList.toggle('hidden'));
document.getElementById('navClose').addEventListener('click', () => nav.classList.add('hidden'));

const PAGE_TITLES = {
  dashboard:'Dashboard', chat:'AI Companion', mood:'Mood Tracker',
  sleep:'Sleep Coach', nutrition:'Nutrition Guide', exercise:'Exercise Planner',
  games:'Stress-Relief Games', journal:'Journal', toolkit:'Wellness Toolkit',
  analytics:'Analytics', profile:'My Profile'
};

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(link.dataset.page);
    if (window.innerWidth <= 680) nav.classList.add('hidden');
  });
});

function navigateTo(page) {
  document.querySelectorAll('.nav-link').forEach(l => l.classList.toggle('active', l.dataset.page === page));
  pageTitle.textContent = PAGE_TITLES[page] || page;
  ({ dashboard, chat, mood, sleep, nutrition, exercise, games, journal, toolkit, analytics, profile }[page] || dashboard)();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const CAP = s => s ? s[0].toUpperCase() + s.slice(1) : s;
const EMJ = { joy:'😊', sadness:'😢', anger:'😠', fear:'😨', disgust:'😣', surprise:'😮', neutral:'😐', anxiety:'😰', stress:'😫', burnout:'🔥' };
const today = () => new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
const isoDate = d => d.toISOString().slice(0,10);
const clamp = (v, mn, mx) => Math.max(mn, Math.min(mx, v));
function getMoodEmoji(s) { return s>=9?'😄':s>=7?'😊':s>=5?'😐':s>=3?'😔':'😢'; }
function scoreCol(v) { return v>=7?'var(--green)':v>=5?'var(--yellow)':'var(--red)'; }

function md(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g,'<em>$1</em>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/^---$/gm,'<hr>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/^[*\-] (.+)$/gm,'<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm,'<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g,'<ul>$1</ul>')
    .replace(/\n{2,}/g,'</p><p>')
    .replace(/\n/g,'<br>')
    .replace(/^(.+)$/,'<p>$1</p>');
}

function loader(msg = 'Loading…') {
  return `<div class="loader"><div class="spinner"></div><span>${msg}</span></div>`;
}

// ── SVG Sparkline ─────────────────────────────────────────────────────────────
function sparkline(values, colour = '#9b7ff5', h = 70) {
  const v = values.map(x => x == null ? null : +x);
  const def = v.filter(x => x != null);
  if (def.length < 2) return `<svg class="line-chart" viewBox="0 0 200 ${h}"><text x="100" y="${h/2}" fill="var(--subtle)" text-anchor="middle" font-size="11">No data yet</text></svg>`;
  const W = 200, pad = 6;
  const mn = Math.min(...def), mx = Math.max(...def) || mn + 1;
  const sx = i => pad + (i / (v.length - 1)) * (W - pad*2);
  const sy = val => h - pad - ((val - mn) / (mx - mn)) * (h - pad*2);
  const pts = v.map((val, i) => val != null ? `${sx(i).toFixed(1)},${sy(val).toFixed(1)}` : null).filter(Boolean).join(' ');
  const dots = def.map((val, i) => `<circle cx="${sx(v.findIndex((x,j)=>x!=null&&j>=i)).toFixed(1)}" cy="${sy(val).toFixed(1)}" r="2.5" fill="${colour}"/>`).join('');
  const apts = `${sx(0)},${h} ${pts} ${sx(v.length-1)},${h}`;
  return `<svg class="line-chart" viewBox="0 0 ${W} ${h}" preserveAspectRatio="none">
    <defs><linearGradient id="sg${colour.replace(/[^a-z0-9]/gi,'')}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${colour}" stop-opacity=".25"/>
      <stop offset="100%" stop-color="${colour}" stop-opacity="0"/>
    </linearGradient></defs>
    <polygon points="${apts}" fill="url(#sg${colour.replace(/[^a-z0-9]/gi,'')})" />
    <polyline points="${pts}" fill="none" stroke="${colour}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    ${dots}
  </svg>`;
}

// ── Donut / ring chart ────────────────────────────────────────────────────────
function donutSVG(score, colour, size = 80) {
  const r = 30, c = size / 2;
  const circ = 2 * Math.PI * r;
  const fill = (score / 10) * circ;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="mood-ring-svg">
    <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="var(--surface3)" stroke-width="7"/>
    <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${colour}" stroke-width="7"
      stroke-dasharray="${fill} ${circ}" stroke-dashoffset="${circ/4}"
      stroke-linecap="round" style="transition:stroke-dasharray .6s"/>
  </svg>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────
async function dashboard() {
  content.innerHTML = loader('Building your dashboard…');
  try {
    // Fetch analytics (fast, no ML needed) + briefing in parallel
    const [anData, moodData] = await Promise.all([
      apiGet(`/analytics/dashboard?user_id=${USER_ID}`),
      apiGet(`/mood/analytics?user_id=${USER_ID}`).catch(() => ({ avg_mood:5, avg_stress:5, top_emotion:'neutral', count:0 })),
    ]);
    const sc = anData.scores;
    const tr = anData.trends;
    const now = new Date();
    const hr = now.getHours();
    const greeting = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';

    content.innerHTML = `
<!-- ── Hero ── -->
<div class="dash-hero">
  <div class="dash-hero-top">
    <div class="dash-greeting">
      <h2>${greeting}, <span class="hi-name">Student</span> ✨</h2>
      <p>Here's your wellness snapshot for today. You've got this.</p>
    </div>
    <div class="dash-date">
      <div style="font-size:18px;font-weight:800;color:var(--text)">${now.getDate()}</div>
      <div>${now.toLocaleDateString('en-US',{month:'long',year:'numeric'})}</div>
      <div>${now.toLocaleDateString('en-US',{weekday:'long'})}</div>
    </div>
  </div>
  <div class="dash-score-row">
    <div class="dsr-tab p" onclick="navigateTo('mood')">
      <div class="dsr-icon">😊</div>
      <div class="dsr-val">${sc.mood_score}</div>
      <div class="dsr-lbl">Mood</div>
    </div>
    <div class="dsr-tab b" onclick="navigateTo('sleep')">
      <div class="dsr-icon">🌙</div>
      <div class="dsr-val">${sc.sleep_score}</div>
      <div class="dsr-lbl">Sleep</div>
    </div>
    <div class="dsr-tab g" onclick="navigateTo('analytics')">
      <div class="dsr-icon">🧘</div>
      <div class="dsr-val">${sc.wellness_score}</div>
      <div class="dsr-lbl">Wellness</div>
    </div>
    <div class="dsr-tab ${sc.stress_score >= 7 ? 'r' : sc.stress_score >= 5 ? 'y' : 'g'}">
      <div class="dsr-icon">😤</div>
      <div class="dsr-val">${sc.stress_score}</div>
      <div class="dsr-lbl">Stress</div>
    </div>
    <div class="dsr-tab t" onclick="navigateTo('exercise')">
      <div class="dsr-icon">🏃</div>
      <div class="dsr-val">${sc.activity_score}</div>
      <div class="dsr-lbl">Activity</div>
    </div>
  </div>
</div>

<!-- ── Grid ── -->
<div class="dash-grid">

  <!-- AI Briefing (full width) -->
  <div class="widget widget-briefing">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">🌅</span> Daily Wellness Briefing</div>
      <button class="btn btn-secondary btn-sm" id="refreshBriefing" style="font-size:11px">↻ Refresh</button>
    </div>
    <div class="widget-body" id="briefingBody">
      <div class="briefing-loading"><div class="sp"></div><span>${mlReady ? 'Generating your personalised briefing…' : 'AI is warming up — briefing will appear shortly…'}</span></div>
    </div>
  </div>

  <!-- Mood Ring -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">😊</span> Mood Overview</div>
      <span class="widget-badge">${moodData.count} entries</span>
    </div>
    <div class="widget-body">
      <div class="mood-ring-wrap">
        ${donutSVG(sc.mood_score, scoreCol(sc.mood_score))}
        <div class="mood-ring-info">
          <div class="mri-score" style="color:${scoreCol(sc.mood_score)}">${sc.mood_score}<span style="font-size:14px;color:var(--muted)">/10</span></div>
          <div class="mri-label">Avg mood · 30 days</div>
          <div class="mri-trend ${sc.mood_score >= 6 ? 'up' : 'down'}">
            ${sc.mood_score >= 6 ? '↑ Trending positive' : '↓ Needs attention'}
          </div>
          <div style="margin-top:8px;font-size:13px;color:var(--muted)">${EMJ[moodData.top_emotion]||'😐'} Most felt: <strong>${CAP(moodData.top_emotion)}</strong></div>
        </div>
      </div>
      <div class="stat-row">
        <div class="stat-pill"><div class="sp-val" style="color:var(--yellow)">${moodData.avg_stress}/10</div><div class="sp-lbl">Stress</div></div>
        <div class="stat-pill"><div class="sp-val" style="color:var(--blue)">${moodData.count}</div><div class="sp-lbl">Logs</div></div>
      </div>
    </div>
  </div>

  <!-- Mood Trend Chart -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">📈</span> Mood Trend</div>
      <span class="widget-badge">14 days</span>
    </div>
    <div class="widget-body">
      <div class="chart-canvas-wrap">
        ${sparkline(tr.mood_series, '#9b7ff5')}
      </div>
      <div class="chart-labels">
        ${tr.dates.filter((_,i)=>i%3===0).slice(0,5).map(d=>`<span>${d.slice(5)}</span>`).join('')}
      </div>
    </div>
  </div>

  <!-- Sleep Chart -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">🌙</span> Sleep Duration</div>
      <span class="widget-badge" style="color:var(--${sc.sleep_score>=7?'green':sc.sleep_score>=5?'yellow':'red'})">${sc.sleep_score}/10</span>
    </div>
    <div class="widget-body">
      <div class="chart-canvas-wrap">
        ${sparkline(tr.sleep_series, '#22c55e')}
      </div>
      <div class="chart-labels">
        ${tr.dates.filter((_,i)=>i%3===0).slice(0,5).map(d=>`<span>${d.slice(5)}</span>`).join('')}
      </div>
      <div class="stat-row" style="margin-top:10px">
        <div class="stat-pill"><div class="sp-val" style="color:var(--green)">${sc.sleep_score}/10</div><div class="sp-lbl">Score</div></div>
      </div>
    </div>
  </div>

  <!-- AI Insight -->
  <div class="widget" style="grid-column:span 2">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">🧠</span> AI Wellness Insight</div>
    </div>
    <div class="widget-body">
      <div class="insight-box" style="border-radius:var(--r);border-left-width:2px">${anData.ai_insight}</div>
    </div>
  </div>

  <!-- Quick Actions -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">⚡</span> Quick Actions</div>
    </div>
    <div class="widget-body">
      <div class="quick-actions">
        <div class="qa-card" onclick="navigateTo('chat')">
          <span class="qa-icon">💬</span>
          <div class="qa-text"><div class="qa-title">Talk to AI</div><div class="qa-sub">Share how you feel</div></div>
        </div>
        <div class="qa-card" onclick="navigateTo('mood')">
          <span class="qa-icon">😊</span>
          <div class="qa-text"><div class="qa-title">Log Mood</div><div class="qa-sub">Track your emotions</div></div>
        </div>
        <div class="qa-card" onclick="navigateTo('sleep')">
          <span class="qa-icon">🌙</span>
          <div class="qa-text"><div class="qa-title">Log Sleep</div><div class="qa-sub">Track last night</div></div>
        </div>
        <div class="qa-card" onclick="navigateTo('journal')">
          <span class="qa-icon">📓</span>
          <div class="qa-text"><div class="qa-title">Write Journal</div><div class="qa-sub">Reflect & release</div></div>
        </div>
        <div class="qa-card" onclick="navigateTo('exercise')">
          <span class="qa-icon">🏃</span>
          <div class="qa-text"><div class="qa-title">Workout Plan</div><div class="qa-sub">Move your body</div></div>
        </div>
        <div class="qa-card" onclick="navigateTo('toolkit')">
          <span class="qa-icon">🧘</span>
          <div class="qa-text"><div class="qa-title">Breathe</div><div class="qa-sub">Calm down now</div></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Wellness Tips -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">💡</span> Today's Wellness Tips</div>
    </div>
    <div class="widget-body">
      ${getTips(sc).map(t => `<div class="tip-card"><div class="tip-label">${t.label}</div>${t.text}</div>`).join('')}
    </div>
  </div>

  <!-- Score Summary -->
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title"><span class="wt-icon">📊</span> Score Summary</div>
    </div>
    <div class="widget-body">
      <div class="emo-bars">
        ${[
          ['Overall Wellness', sc.wellness_score, 'var(--purple-h)'],
          ['Mood', sc.mood_score, 'var(--blue)'],
          ['Sleep', sc.sleep_score, 'var(--green)'],
          ['Low Stress', clamp(10 - sc.stress_score, 0, 10), 'var(--teal)'],
          ['Activity', sc.activity_score, 'var(--yellow)'],
        ].map(([name, val, col]) => `
          <div class="emo-row">
            <span class="er-name">${name}</span>
            <div class="er-bar-bg"><div class="er-bar-fill" style="width:${val*10}%;background:${col}"></div></div>
            <span class="er-pct">${val}/10</span>
          </div>`).join('')}
      </div>
    </div>
  </div>

</div>`;

    // Async: load briefing separately (may require ML)
    loadBriefing();
    document.getElementById('refreshBriefing').addEventListener('click', loadBriefing);

  } catch(e) {
    content.innerHTML = `<div class="page-section"><div class="card"><p>Dashboard error: ${e.message}<br>Make sure the server is running: <code>python api_server.py</code></p></div></div>`;
  }
}

async function loadBriefing() {
  const el = document.getElementById('briefingBody');
  if (!el) return;
  el.innerHTML = `<div class="briefing-loading"><div class="sp"></div><span>Generating your personalised daily briefing…</span></div>`;
  try {
    const b = await apiFetch(`/wellness/daily-briefing?user_id=${USER_ID}`, {}, 100000);
    if (!document.getElementById('briefingBody')) return;
    el.innerHTML = `<div class="briefing-text">${b.briefing}</div>`;
  } catch(e) {
    if (!document.getElementById('briefingBody')) return;
    if (!mlReady) {
      // Auto-retry once AI is ready
      el.innerHTML = `<div style="font-size:13px;color:var(--muted);padding:4px 0">
        AI is warming up… your briefing will appear automatically once ready
        <span style="display:inline-block;margin-left:6px;color:var(--yellow);animation:pulse 1.2s ease-in-out infinite">●</span>
      </div>`;
      const retry = setInterval(async () => {
        if (!document.getElementById('briefingBody')) { clearInterval(retry); return; }
        if (mlReady) { clearInterval(retry); loadBriefing(); }
      }, 5000);
    } else {
      el.innerHTML = `<div style="font-size:13px;color:var(--muted);padding:4px 0">
        Could not load briefing right now.
        <button class="btn btn-secondary btn-sm" onclick="loadBriefing()" style="margin-left:10px">Retry</button>
      </div>`;
    }
  }
}

function getTips(sc) {
  const tips = [];
  if (sc.stress_score >= 7) tips.push({ label: '😤 High Stress', text: 'Try the 4-4-6 breathing: inhale 4s, hold 4s, exhale 6s. Repeat 5 times.' });
  if (sc.sleep_score < 6) tips.push({ label: '🌙 Sleep Tip', text: 'Put your phone away 30 min before bed. Blue light disrupts melatonin production.' });
  if (sc.mood_score < 5) tips.push({ label: '😊 Mood Boost', text: 'A 10-minute walk outside increases serotonin and norepinephrine within minutes.' });
  if (sc.activity_score < 5) tips.push({ label: '🏃 Move More', text: 'Even 5 minutes of movement — stretching, dancing, walking — resets your energy.' });
  tips.push({ label: '💧 Hydration', text: 'Aim for 8 glasses of water today. Dehydration directly worsens focus and mood.' });
  tips.push({ label: '🧘 Mindfulness', text: 'Take one mindful minute: close your eyes, focus on your breath, label thoughts as they come.' });
  return tips.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. CHAT
// ─────────────────────────────────────────────────────────────────────────────
function chat() {
  content.innerHTML = `
  <div class="chat-layout">
    <div class="chat-messages" id="chatMsgs">
      <div class="welcome-wrap">
        <div style="font-size:54px;margin-bottom:16px">🧠</div>
        <h2>Hi, I'm your AI wellness companion</h2>
        <p>Share how you're feeling — I'll listen, understand, and support you with empathy and evidence-based guidance.</p>
        <div class="chip-grid">
          <button class="chip" data-msg="I'm really stressed about my exams and can't concentrate.">😰 Exam stress</button>
          <button class="chip" data-msg="I feel lonely and disconnected from everyone.">😔 Loneliness</button>
          <button class="chip" data-msg="I'm completely burned out with no motivation.">🔥 Burnout</button>
          <button class="chip" data-msg="I'm anxious about my future career.">😟 Career anxiety</button>
          <button class="chip" data-msg="Can you help me relax right now?">🧘 Relax me</button>
          <button class="chip" data-msg="I need help managing my study time.">📚 Study help</button>
        </div>
      </div>
    </div>
    <div id="emotionStrip" style="display:none" class="emotion-strip">
      <span class="em-label" id="emLabel">—</span>
      <div class="em-bar-bg"><div class="em-bar-fill" id="emBar" style="width:0%"></div></div>
      <span class="em-text" id="emText">—</span>
      <span class="risk-badge" id="riskBadge">—</span>
    </div>
    <div class="chat-input-area">
      <div class="chat-input-wrap">
        <textarea id="chatIn" rows="1" placeholder="Share what's on your mind…" maxlength="4000"></textarea>
        <button class="send-btn" id="chatSend" disabled>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p class="input-disc">Not a substitute for professional mental health care. In crisis? Call emergency services immediately.</p>
    </div>
  </div>`;

  const msgs = document.getElementById('chatMsgs');
  const inp  = document.getElementById('chatIn');
  const btn  = document.getElementById('chatSend');

  const upd = () => btn.disabled = chatLoading || !inp.value.trim();
  inp.addEventListener('input', () => { inp.style.height='auto'; inp.style.height=Math.min(inp.scrollHeight,130)+'px'; upd(); });
  inp.addEventListener('keydown', e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!btn.disabled)doSend();} });
  btn.addEventListener('click', doSend);
  document.querySelectorAll('.chip[data-msg]').forEach(c => c.addEventListener('click', () => { inp.value=c.dataset.msg; upd(); doSend(); }));

  function addMsg(role, text, extra = {}) {
    document.querySelector('.welcome-wrap')?.remove();
    const row = document.createElement('div');
    row.className = `msg-row ${role}${extra.crisis?' crisis-msg':''}`;
    const av = `<div class="av">${role==='user'?'🧑':'🧠'}</div>`;
    const bbl = document.createElement('div'); bbl.className = 'bubble';
    if (role === 'assistant') {
      bbl.innerHTML = md(text);
      if (extra.recs?.length) {
        const rc = document.createElement('div'); rc.className = 'rec-chips';
        extra.recs.forEach(r => { const ch = document.createElement('span'); ch.className=`rec-chip${r.has_physical_activity?' phys':''}`; ch.textContent=`${r.has_physical_activity?'🏃 ':'💡 '}${r.title} · ${r.duration_minutes}m`; rc.appendChild(ch); });
        bbl.appendChild(rc);
      }
    } else { bbl.textContent = text; }
    row.innerHTML = av; row.appendChild(bbl);
    msgs.appendChild(row); msgs.scrollTop = msgs.scrollHeight;
  }

  let _typingTimer = null;

  function showTyping() {
    const row = document.createElement('div'); row.className='msg-row assistant'; row.id='tyRow';
    row.innerHTML = `<div class="av">🧠</div>
      <div style="display:flex;align-items:center;gap:10px">
        <div class="typing-ind"><div class="ty-dot"></div><div class="ty-dot"></div><div class="ty-dot"></div></div>
        <span id="thinkTimer" style="font-size:11px;color:var(--subtle)">Thinking…</span>
      </div>`;
    msgs.appendChild(row); msgs.scrollTop = msgs.scrollHeight;
    // Live elapsed counter
    const t0 = Date.now();
    _typingTimer = setInterval(() => {
      const el = document.getElementById('thinkTimer');
      if (el) el.textContent = `Thinking… ${((Date.now()-t0)/1000).toFixed(0)}s`;
    }, 1000);
  }

  function hideTyping() {
    clearInterval(_typingTimer); _typingTimer = null;
    document.getElementById('tyRow')?.remove();
  }

  async function doSend() {
    const text = inp.value.trim(); if(!text||chatLoading) return;
    addMsg('user', text); inp.value=''; inp.style.height='auto';
    chatLoading=true; upd(); showTyping();
    try {
      // 150s timeout for chat — AI can be slow on first response
      const d = await apiFetch('/chat', { method:'POST', body:JSON.stringify({ message:text, session_id:chatSessionId, user_id:USER_ID, include_physical:true }) }, 150000);
      hideTyping();
      chatSessionId = d.session_id;
      addMsg('assistant', d.response, { crisis:d.was_crisis, recs:d.recommendations });
      // Update emotion strip with rich analysis
      const strip = document.getElementById('emotionStrip');
      strip.style.display='flex';
      const cols = {Low:'var(--green)',Medium:'var(--yellow)',High:'var(--red)'};
      const em = d.emotion;
      // Primary + secondary emotion label
      const secLabel = em.secondary_emotion && em.secondary_emotion !== 'neutral'
        ? ` <span style="font-size:11px;opacity:.7">+ ${em.secondary_emotion}</span>` : '';
      document.getElementById('emLabel').innerHTML =
        `${EMJ[em.primary_emotion]||'🧠'} <strong>${CAP(em.primary_emotion)}</strong>${secLabel}`;
      document.getElementById('emBar').style.width=`${em.intensity*10}%`;
      document.getElementById('emBar').style.background=cols[em.risk_level]||'var(--purple)';
      // Show intensity + valence + arousal
      const valSign = em.valence >= 0 ? '+' : '';
      document.getElementById('emText').textContent=
        `${em.intensity}/10 · val ${valSign}${(em.valence||0).toFixed(2)} · aro ${(em.arousal||0).toFixed(2)}`;
      const rb=document.getElementById('riskBadge'); rb.textContent=em.risk_level; rb.className=`risk-badge ${em.risk_level}`;
      // Show nuances as small pill row below strip
      const nuances = em.emotion_nuances||[];
      let nuanceEl = document.getElementById('emNuances');
      if (!nuanceEl) {
        nuanceEl = document.createElement('div');
        nuanceEl.id = 'emNuances';
        nuanceEl.style.cssText='display:flex;gap:6px;flex-wrap:wrap;padding:4px 12px 6px;';
        strip.after(nuanceEl);
      }
      nuanceEl.innerHTML = nuances.map(n =>
        `<span style="font-size:10.5px;background:var(--surface3);border:1px solid var(--border);
          border-radius:20px;padding:2px 8px;color:var(--muted)">${n}</span>`
      ).join('');
      if(d.was_crisis) document.getElementById('crisisBanner').style.display='block';
    } catch(e) {
      hideTyping();
      addMsg('assistant', `⚠️ ${e.message}`);
    }
    chatLoading=false; upd(); inp.focus();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. MOOD
// ─────────────────────────────────────────────────────────────────────────────
async function mood() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Log Today's Mood</p>
    <div class="card">
      <div class="mood-picker">
        ${[['😄','10','Great'],['😊','8','Good'],['😐','6','Okay'],['😔','4','Low'],['😢','2','Sad'],['😠','2','Angry'],['😰','3','Anxious'],['😫','2','Exhausted']].map(([e,v,l])=>`<button class="mood-btn" data-val="${v}"><span>${e}</span><span class="mood-label">${l}</span></button>`).join('')}
      </div>
      <div class="form-group"><label>How are you feeling? (optional)</label><textarea id="moodNote" placeholder="Write anything on your mind…"></textarea></div>
      <div class="form-group"><label>Stress Level: <span id="sv" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="sr" min="1" max="10" value="5"/></div></div>
      <div class="form-group"><label>Energy Level: <span id="ev" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="er" min="1" max="10" value="5"/></div></div>
      <button class="btn btn-primary" id="logMoodBtn">Log Mood</button>
    </div>
  </div>
  <div class="page-section"><p class="section-title">Mood History</p><div id="moodHist">${loader()}</div></div>`;

  let sel = 5;
  document.querySelectorAll('.mood-btn').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('.mood-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); sel=+b.dataset.val; }));
  document.getElementById('sr').addEventListener('input', e => document.getElementById('sv').textContent=e.target.value);
  document.getElementById('er').addEventListener('input', e => document.getElementById('ev').textContent=e.target.value);
  document.getElementById('logMoodBtn').addEventListener('click', async () => {
    const btn=document.getElementById('logMoodBtn'); btn.disabled=true; btn.textContent='Logging…';
    try { await apiPost('/mood/log',{user_id:USER_ID,mood_score:sel,note:document.getElementById('moodNote').value,stress_score:+document.getElementById('sr').value,energy_score:+document.getElementById('er').value}); toast('Mood logged ✓'); loadMoodHist(); }
    catch(e){toast(e.message,'error');} btn.disabled=false; btn.textContent='Log Mood';
  });

  async function loadMoodHist() {
    const el=document.getElementById('moodHist');
    try {
      const [logs,ana]=await Promise.all([apiGet(`/mood/history?user_id=${USER_ID}`),apiGet(`/mood/analytics?user_id=${USER_ID}`)]);
      const series=logs.map(l=>l.mood_score).reverse(), labels=logs.map(l=>l.logged_at.slice(5,10)).reverse();
      el.innerHTML=`
        <div class="card" style="margin-bottom:14px">
          <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:14px">
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Avg Mood</div><div style="font-size:26px;font-weight:800;color:var(--purple-h)">${ana.avg_mood}/10</div></div>
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Avg Stress</div><div style="font-size:26px;font-weight:800;color:var(--yellow)">${ana.avg_stress}/10</div></div>
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Top Emotion</div><div style="font-size:22px;font-weight:800">${EMJ[ana.top_emotion]||'😐'} ${CAP(ana.top_emotion)}</div></div>
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Total Logs</div><div style="font-size:26px;font-weight:800;color:var(--blue)">${ana.count}</div></div>
          </div>
          <div class="chart-canvas-wrap">${sparkline(series,'#9b7ff5')}</div>
        </div>
        ${logs.slice(0,10).map(l=>`<div class="card" style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px"><strong>${getMoodEmoji(l.mood_score)} Mood ${l.mood_score}/10</strong><span style="font-size:11px;color:var(--subtle)">${l.logged_at.slice(0,16).replace('T',' ')}</span></div>${l.note?`<p style="font-size:13px;color:var(--muted)">${l.note}</p>`:''}<div style="display:flex;gap:12px;margin-top:5px;font-size:12px;color:var(--subtle)"><span>Stress: ${l.stress_score}/10</span><span>Energy: ${l.energy_score}/10</span></div></div>`).join('')}`;
    } catch { el.innerHTML=`<div class="card"><p>No mood history yet. Log your first mood above!</p></div>`; }
  }
  loadMoodHist();
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. SLEEP
// ─────────────────────────────────────────────────────────────────────────────
async function sleep() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Log Last Night's Sleep</p>
    <div class="card">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="form-group"><label>Bedtime</label><input type="time" id="bt" value="23:00"/></div>
        <div class="form-group"><label>Wake Time</label><input type="time" id="wt" value="07:00"/></div>
      </div>
      <div class="form-group"><label>Sleep Quality: <span id="sqv" class="range-val">7</span>/10</label><div class="range-wrap"><input type="range" id="sqr" min="1" max="10" value="7"/></div></div>
      <div class="form-group"><label>Notes (optional)</label><textarea id="sn" placeholder="What affected your sleep?"></textarea></div>
      <button class="btn btn-primary" id="logSleepBtn">Log Sleep</button>
    </div>
  </div>
  <div class="page-section">
    <p class="section-title">AI Sleep Plan</p>
    <div id="sleepPlan"><button class="btn btn-secondary" id="getSleepPlan">✨ Generate My Sleep Plan</button></div>
  </div>
  <div class="page-section"><p class="section-title">Sleep History</p><div id="sleepHist">${loader()}</div></div>`;

  document.getElementById('sqr').addEventListener('input', e => document.getElementById('sqv').textContent=e.target.value);
  document.getElementById('logSleepBtn').addEventListener('click', async () => {
    const btn=document.getElementById('logSleepBtn'); btn.disabled=true; btn.textContent='Logging…';
    const b=document.getElementById('bt').value, w=document.getElementById('wt').value;
    const [bh,bm]=b.split(':').map(Number),[wh,wm]=w.split(':').map(Number);
    let mins=(wh*60+wm)-(bh*60+bm); if(mins<0)mins+=1440;
    const dur=Math.round(mins/60*10)/10;
    try {
      const r=await apiPost('/sleep/log',{user_id:USER_ID,bedtime:b,wake_time:w,duration_hours:dur,quality_score:+document.getElementById('sqr').value,notes:document.getElementById('sn').value});
      toast(`Sleep logged! Score: ${r.sleep_score}/10 ✓`); loadSleepHist();
    } catch(e){toast(e.message,'error');}
    btn.disabled=false; btn.textContent='Log Sleep';
  });
  document.getElementById('getSleepPlan').addEventListener('click', async () => {
    const area=document.getElementById('sleepPlan'); area.innerHTML=loader('Generating sleep plan…');
    try {
      const p=await apiFetch(`/sleep/plan?user_id=${USER_ID}`,{},120000);
      area.innerHTML=`
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
          ${[['🌙','Sleep Score',p.sleep_score+'/10',scoreCol(p.sleep_score)],['⏱','Avg Duration',p.avg_duration+'h',p.avg_duration>=7?'var(--green)':'var(--yellow)'],['⭐','Avg Quality',p.avg_quality+'/10',scoreCol(p.avg_quality)]].map(([i,l,v,c])=>`<div class="card" style="margin:0;text-align:center"><div style="font-size:20px">${i}</div><div style="font-size:11px;color:var(--muted);margin:3px 0">${l}</div><div style="font-size:20px;font-weight:800;color:${c}">${v}</div></div>`).join('')}
        </div>
        <div class="ai-block">${p.plan}</div>`;
    } catch(e){area.innerHTML=`<div class="card"><p>${e.message}</p></div>`;}
  });
  async function loadSleepHist() {
    const el=document.getElementById('sleepHist');
    try {
      const logs=await apiGet(`/sleep/history?user_id=${USER_ID}`);
      const durations=logs.map(l=>l.duration_hours).reverse(), labels=logs.map(l=>l.date.slice(5)).reverse();
      const avg=logs.length?Math.round(logs.reduce((s,l)=>s+l.duration_hours,0)/logs.length*10)/10:0;
      el.innerHTML=`
        <div class="card" style="margin-bottom:12px">
          <div style="display:flex;gap:20px;margin-bottom:12px">
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase">Avg Duration</div><div style="font-size:22px;font-weight:800;color:var(--green)">${avg}h</div></div>
            <div><div style="font-size:11px;color:var(--muted);text-transform:uppercase">Nights Logged</div><div style="font-size:22px;font-weight:800;color:var(--blue)">${logs.length}</div></div>
          </div>
          <div class="chart-canvas-wrap">${sparkline(durations,'#22c55e')}</div>
        </div>
        ${logs.slice(0,7).map(l=>`<div class="card" style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><strong>🌙 ${l.date}</strong><span class="risk-badge ${l.sleep_score>=7?'Low':l.sleep_score>=5?'Medium':'High'}">${l.sleep_score}/10</span></div><div style="margin-top:6px;font-size:13px;color:var(--muted)">${l.bedtime} → ${l.wake_time} · ${l.duration_hours}h · Quality: ${l.quality_score}/10</div>${l.notes?`<p style="font-size:12px;color:var(--subtle);margin-top:5px">${l.notes}</p>`:''}</div>`).join('')}`;
    } catch { el.innerHTML=`<div class="card"><p>No sleep history yet.</p></div>`; }
  }
  loadSleepHist();
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. NUTRITION
// ─────────────────────────────────────────────────────────────────────────────
async function nutrition() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Generate Today's Meal Plan</p>
    <div class="card">
      <div class="form-group"><label>Current Mood: <span id="nmv" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="nm" min="1" max="10" value="5"/></div></div>
      <div class="form-group"><label>Stress Level: <span id="nsv" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="ns" min="1" max="10" value="5"/></div></div>
      <button class="btn btn-primary" id="getMealPlan">✨ Get My Meal Plan</button>
    </div>
  </div>
  <div id="mealPlanArea"></div>
  <div class="page-section"><p class="section-title">🧘 Stress-Reducing Foods</p><div id="stressFoods">${loader()}</div></div>`;
  document.getElementById('nm').addEventListener('input',e=>document.getElementById('nmv').textContent=e.target.value);
  document.getElementById('ns').addEventListener('input',e=>document.getElementById('nsv').textContent=e.target.value);
  document.getElementById('getMealPlan').addEventListener('click', async()=>{
    const area=document.getElementById('mealPlanArea'); area.innerHTML=loader('Generating personalised meal plan…');
    try { const p=await apiFetch('/nutrition/meal-plan',{method:'POST',body:JSON.stringify({user_id:USER_ID,mood_score:+document.getElementById('nm').value,stress_level:+document.getElementById('ns').value})},120000); area.innerHTML=`<div class="page-section"><p class="section-title">Your Personalised Meal Plan</p><div class="ai-block">${p.meal_plan}</div></div>`; }
    catch(e){area.innerHTML=`<div class="page-section"><div class="card"><p>⚠️ ${e.message}</p></div></div>`;}
  });
  try {
    const foods=await apiGet('/nutrition/stress-foods');
    document.getElementById('stressFoods').innerHTML=`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">${foods.map(f=>`<div class="card" style="margin:0"><strong style="font-size:13px">🥗 ${f.name}</strong><p style="margin-top:6px;font-size:12.5px">${f.benefit}</p></div>`).join('')}</div>`;
  } catch { document.getElementById('stressFoods').innerHTML='<p style="color:var(--muted)">Could not load.</p>'; }
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. EXERCISE
// ─────────────────────────────────────────────────────────────────────────────
async function exercise() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Generate Workout Plan</p>
    <div class="card">
      <div class="form-group"><label>Stress Level: <span id="exsv" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="exs" min="1" max="10" value="5"/></div></div>
      <div class="form-group"><label>Energy Level: <span id="exev" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="exe" min="1" max="10" value="5"/></div></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="form-group"><label>Available Time (min)</label><input type="number" id="ext" value="30" min="5" max="120"/></div>
        <div class="form-group"><label>Environment</label><select id="exenv"><option value="any">Any</option><option value="indoor">Indoor</option><option value="outdoor">Outdoor</option></select></div>
      </div>
      <button class="btn btn-primary" id="getWorkout">✨ Generate Workout</button>
    </div>
  </div>
  <div id="workoutArea"></div>
  <div class="page-section">
    <p class="section-title">Log an Activity</p>
    <div class="card">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px">
        <div class="form-group"><label>Activity</label><input type="text" id="exact" placeholder="Running, Yoga…"/></div>
        <div class="form-group"><label>Duration (min)</label><input type="number" id="exdur" value="30" min="1"/></div>
        <div class="form-group"><label>Intensity</label><select id="exint"><option>low</option><option selected>moderate</option><option>high</option></select></div>
      </div>
      <button class="btn btn-secondary btn-sm" id="logExBtn">Log Activity</button>
    </div>
  </div>
  <div class="page-section"><p class="section-title">Recent Activity</p><div id="exHist">${loader()}</div></div>`;
  document.getElementById('exs').addEventListener('input',e=>document.getElementById('exsv').textContent=e.target.value);
  document.getElementById('exe').addEventListener('input',e=>document.getElementById('exev').textContent=e.target.value);
  document.getElementById('getWorkout').addEventListener('click', async()=>{
    const a=document.getElementById('workoutArea'); a.innerHTML=loader('Building your workout plan…');
    try { const p=await apiFetch('/exercise/plan',{method:'POST',body:JSON.stringify({user_id:USER_ID,stress_level:+document.getElementById('exs').value,energy_level:+document.getElementById('exe').value,available_minutes:+document.getElementById('ext').value,environment:document.getElementById('exenv').value})},120000); a.innerHTML=`<div class="page-section"><p class="section-title">Your Workout Plan</p><div class="ai-block">${p.workout_plan}</div></div>`; }
    catch(e){a.innerHTML=`<div class="page-section"><div class="card"><p>⚠️ ${e.message}</p></div></div>`;}
  });
  document.getElementById('logExBtn').addEventListener('click', async()=>{
    const btn=document.getElementById('logExBtn'); btn.disabled=true;
    try { await apiPost('/exercise/log',{user_id:USER_ID,activity_type:document.getElementById('exact').value||'general',duration_min:+document.getElementById('exdur').value,intensity:document.getElementById('exint').value}); toast('Activity logged ✓'); loadExHist(); }
    catch(e){toast(e.message,'error');} btn.disabled=false;
  });
  async function loadExHist(){
    const el=document.getElementById('exHist');
    try {
      const logs=await apiGet(`/exercise/history?user_id=${USER_ID}`);
      if(!logs.length){el.innerHTML=`<div class="card"><p>No activities yet. Log your first workout above!</p></div>`;return;}
      el.innerHTML=logs.slice(0,8).map(l=>`<div class="card" style="margin-bottom:8px"><div style="display:flex;justify-content:space-between"><strong>🏃 ${l.activity_type}</strong><span style="font-size:11px;color:var(--subtle)">${l.logged_at.slice(0,10)}</span></div><div style="margin-top:5px;font-size:13px;color:var(--muted)">${l.duration_min} min · ${l.intensity}</div></div>`).join('');
    } catch{el.innerHTML=`<div class="card"><p>Could not load history.</p></div>`;}
  }
  loadExHist();
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. GAMES
// ─────────────────────────────────────────────────────────────────────────────
async function games() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Find Stress-Relief Activities</p>
    <div class="card" style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end">
      <div class="form-group" style="flex:1;min-width:100px;margin:0"><label>Energy</label><select id="gEnergy"><option value="7">High</option><option value="5" selected>Medium</option><option value="2">Low</option></select></div>
      <div class="form-group" style="flex:1;min-width:100px;margin:0"><label>Space</label><select id="gSpace"><option value="any">Any</option><option value="indoor">Indoor</option><option value="outdoor">Outdoor</option></select></div>
      <div class="form-group" style="flex:1;min-width:100px;margin:0"><label>Participants</label><select id="gPart"><option value="1">Solo</option><option value="2" selected>2+</option><option value="4">Group</option></select></div>
      <button class="btn btn-primary btn-sm" id="getGames">🎮 Find</button>
    </div>
  </div>
  <div id="gamesList" class="game-grid">${loader()}</div>`;
  async function loadGames(){
    const el=document.getElementById('gamesList'); el.innerHTML=loader();
    try {
      const g=await apiPost('/exercise/games',{energy:+document.getElementById('gEnergy').value,space:document.getElementById('gSpace').value,participants:+document.getElementById('gPart').value,low_mobility:false});
      if(!g.length){el.innerHTML=`<div class="card"><p>No matches. Try different filters.</p></div>`;return;}
      el.innerHTML=g.map(g=>`<div class="game-card"><h3>${g.name} <span class="game-cat">${g.category.replace('_',' ')}</span></h3><p>${g.benefits}</p><p><strong>How to play:</strong> ${g.rules}</p><p style="font-style:italic;font-size:12px;color:var(--subtle)">${g.suitability}</p><div class="game-meta"><span>⏱ ${g.duration_min} min</span><span>👥 ${g.participants}</span><span>⚡ ${g.energy}</span></div></div>`).join('');
    } catch(e){el.innerHTML=`<div class="card"><p>${e.message}</p></div>`;}
  }
  document.getElementById('getGames').addEventListener('click',loadGames);
  loadGames();
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. JOURNAL
// ─────────────────────────────────────────────────────────────────────────────
async function journal() {
  content.innerHTML = `
  <div class="page-section">
    <p class="section-title">Write a Journal Entry</p>
    <div class="card">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="form-group"><label>Entry Type</label><select id="jType"><option value="reflection">Reflection</option><option value="gratitude">Gratitude</option><option value="anxiety">Anxiety Processing</option><option value="goal">Goal Setting</option></select></div>
        <div class="form-group"><label>Mood Before: <span id="jmv" class="range-val">5</span>/10</label><div class="range-wrap"><input type="range" id="jm" min="1" max="10" value="5"/></div></div>
      </div>
      <div id="promptBox" style="margin-bottom:14px;padding:10px 14px;background:var(--purple-dim);border-radius:var(--r);font-size:13px;color:var(--purple-h);cursor:pointer;border:1px solid var(--border)">💭 Loading prompt…</div>
      <div class="form-group"><label>Your Journal Entry</label><textarea id="jContent" rows="6" placeholder="Write freely… this is your safe space." style="min-height:120px"></textarea></div>
      <button class="btn btn-primary" id="submitJournal">✨ Save & Get AI Insight</button>
    </div>
    <div id="insightArea"></div>
  </div>
  <div class="page-section"><p class="section-title">Past Entries</p><div id="jHist">${loader()}</div></div>`;
  document.getElementById('jm').addEventListener('input',e=>document.getElementById('jmv').textContent=e.target.value);
  async function loadPrompt(){
    try { const p=await apiGet(`/journal/prompt?entry_type=${document.getElementById('jType').value}`); const b=document.getElementById('promptBox'); b.textContent=`💭 ${p.prompt}`; b.onclick=()=>{const ta=document.getElementById('jContent'); ta.value+=(ta.value?'\n':'')+p.prompt+' ';}; } catch{}
  }
  document.getElementById('jType').addEventListener('change',loadPrompt);
  loadPrompt();
  document.getElementById('submitJournal').addEventListener('click', async()=>{
    const val=document.getElementById('jContent').value.trim();
    if(!val){toast('Please write something first!','error');return;}
    const btn=document.getElementById('submitJournal'); btn.disabled=true; btn.textContent='Analysing…';
    document.getElementById('insightArea').innerHTML=loader('AI is reading your entry…');
    try {
      const r=await apiFetch('/journal/entry',{method:'POST',body:JSON.stringify({user_id:USER_ID,content:val,entry_type:document.getElementById('jType').value,mood_before:+document.getElementById('jm').value})},120000);
      document.getElementById('insightArea').innerHTML=`<div class="card" style="border-left:3px solid var(--purple);border-radius:0 var(--r2) var(--r2) 0"><div class="card-title">🧠 AI Reflection</div><div class="ai-block" style="background:none;border:none;padding:0">${r.insight}</div><div style="margin-top:12px;padding:9px 12px;background:var(--purple-dim);border-radius:var(--r);font-size:13px;color:var(--purple-h)">💭 Next prompt: <em>${r.next_prompt}</em></div></div>`;
      document.getElementById('jContent').value=''; toast('Journal saved ✓'); loadJHist();
    } catch(e){document.getElementById('insightArea').innerHTML=`<div class="card"><p>${e.message}</p></div>`;}
    btn.disabled=false; btn.textContent='✨ Save & Get AI Insight';
  });
  async function loadJHist(){
    const el=document.getElementById('jHist');
    try {
      const entries=await apiGet(`/journal/entries?user_id=${USER_ID}`);
      if(!entries.length){el.innerHTML=`<div class="card"><p>No entries yet. Start writing above!</p></div>`;return;}
      el.innerHTML=entries.map(e=>`<div class="journal-entry"><div class="je-meta">${e.created_at.slice(0,16).replace('T',' ')} · ${CAP(e.entry_type)}</div><div class="je-content">${e.content}</div>${e.ai_insight?`<div class="je-insight">${e.ai_insight.slice(0,300)}${e.ai_insight.length>300?'…':''}</div>`:''}</div>`).join('');
    } catch{el.innerHTML=`<div class="card"><p>Could not load entries.</p></div>`;}
  }
  loadJHist();
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. TOOLKIT
// ─────────────────────────────────────────────────────────────────────────────
async function toolkit() {
  content.innerHTML=`<div id="tkContent">${loader()}</div>`;
  try {
    const d=await apiGet('/wellness/toolkit');
    const icons={breathing:'🌬️',mindfulness:'🧘',cbt:'🧠'};
    const cols={breathing:'var(--blue)',mindfulness:'var(--green)',cbt:'var(--yellow)'};
    let html='<div class="toolkit-grid">';
    for(const[cat,items] of Object.entries(d)){
      for(const item of items){
        html+=`<div class="toolkit-card"><h3>${icons[cat]||'✨'} ${item.name}</h3><ol class="step-list">${item.steps.map(s=>`<li>${s}</li>`).join('')}</ol><span class="dur-badge" style="border-left:2px solid ${cols[cat]||'var(--purple)'};border-radius:0 6px 6px 0">⏱ ${item.duration}</span></div>`;
      }
    }
    html+=`
      <div class="toolkit-card"><h3>💪 Progressive Muscle Relax</h3><ol class="step-list"><li>Sit or lie comfortably</li><li>Tense feet for 5s, release</li><li>Move up: calves → thighs → core</li><li>Continue → fists → arms → shoulders → face</li><li>Breathe slowly throughout</li></ol><span class="dur-badge" style="border-left:2px solid var(--purple);border-radius:0 6px 6px 0">⏱ 10 min</span></div>
      <div class="toolkit-card"><h3>🚿 Cold Water Reset</h3><ol class="step-list"><li>Go to a sink and run cold water</li><li>Splash face 3–5 times</li><li>Hold wrists under cold water 30s</li><li>Take three slow deep breaths</li></ol><span class="dur-badge" style="border-left:2px solid var(--teal);border-radius:0 6px 6px 0">⏱ 2 min</span></div>
      <div class="toolkit-card"><h3>🖊️ Worry Dump</h3><ol class="step-list"><li>Set a 5-minute timer</li><li>Write every worry freely — no filter</li><li>Circle the one you can control right now</li><li>Write one small step toward it</li><li>Close the notebook — worries are contained</li></ol><span class="dur-badge" style="border-left:2px solid var(--orange);border-radius:0 6px 6px 0">⏱ 5 min</span></div>`;
    html+='</div>';
    document.getElementById('tkContent').innerHTML=html;
  } catch(e){document.getElementById('tkContent').innerHTML=`<div class="page-section"><div class="card"><p>${e.message}</p></div></div>`;}
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. ANALYTICS
// ─────────────────────────────────────────────────────────────────────────────
async function analytics() {
  content.innerHTML=`<div class="analytics-layout" id="analyticsContent">${loader('Computing your wellness analytics…')}</div>`;
  try {
    const d=await apiGet(`/analytics/dashboard?user_id=${USER_ID}`);
    const sc=d.scores;
    document.getElementById('analyticsContent').innerHTML=`
      <div>
        <p class="section-title">Wellness Scores</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">
          ${[['🧘','Wellness',sc.wellness_score,'var(--purple-h)'],['😊','Mood',sc.mood_score,'var(--blue)'],['🌙','Sleep',sc.sleep_score,'var(--green)'],['😤','Stress (low=good)',clamp(10-sc.stress_score,0,10),'var(--teal)'],['🏃','Activity',sc.activity_score,'var(--yellow)']].map(([i,l,v,c])=>`<div class="card" style="margin:0;text-align:center"><div style="font-size:22px">${i}</div><div style="font-size:11px;color:var(--muted);margin:3px 0">${l}</div><div style="font-size:24px;font-weight:800;color:${c}">${v}</div><div style="font-size:10px;color:var(--subtle)">/10</div></div>`).join('')}
        </div>
      </div>
      <div>
        <p class="section-title">AI Wellness Insight</p>
        <div class="insight-box">${d.ai_insight}</div>
      </div>
      <div>
        <p class="section-title">Mood Trend (14 days)</p>
        <div class="card chart-wrap">
          <div class="chart-canvas-wrap">${sparkline(d.trends.mood_series,'#9b7ff5',90)}</div>
          <div class="chart-labels">${d.trends.dates.filter((_,i)=>i%2===0).map(dd=>`<span>${dd.slice(5)}</span>`).join('')}</div>
        </div>
      </div>
      <div>
        <p class="section-title">Sleep Trend (14 days)</p>
        <div class="card chart-wrap">
          <div class="chart-canvas-wrap">${sparkline(d.trends.sleep_series,'#22c55e',90)}</div>
          <div class="chart-labels">${d.trends.dates.filter((_,i)=>i%2===0).map(dd=>`<span>${dd.slice(5)}</span>`).join('')}</div>
        </div>
      </div>`;
  } catch(e){document.getElementById('analyticsContent').innerHTML=`<div class="card"><p>${e.message}</p></div>`;}
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. PROFILE
// ─────────────────────────────────────────────────────────────────────────────
async function profile() {
  content.innerHTML = `<div id="profileContent">${loader('Loading your profile…')}</div>`;

  // Load existing profile data first
  let existing = {};
  try {
    existing = await apiGet(`/user/${USER_ID}`);
  } catch {}

  const actOpts = ['sedentary','light','moderate','active','very_active'].map(v =>
    `<option value="${v}" ${(existing.activity_level||'moderate')===v?'selected':''}>${CAP(v.replace('_',' '))}</option>`).join('');
  const fitOpts = ['beginner','intermediate','advanced'].map(v =>
    `<option value="${v}" ${(existing.fitness_level||'beginner')===v?'selected':''}>${CAP(v)}</option>`).join('');

  let dietPrefs = [];
  try { dietPrefs = JSON.parse(existing.diet_prefs || '[]'); } catch {}
  let wellnessGoals = [];
  try { wellnessGoals = JSON.parse(existing.wellness_goals || '[]'); } catch {}

  const allDiets = ['vegetarian','vegan','gluten-free','dairy-free','halal','kosher','no-restrictions'];
  const allGoals = ['reduce stress','improve sleep','boost energy','build fitness','improve focus','manage anxiety','eat healthier'];

  document.getElementById('profileContent').innerHTML = `
  <div class="page-section">
    <p class="section-title">Personal Information</p>
    <div class="card">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="form-group"><label>Name</label><input type="text" id="pName" value="${existing.name||'Student'}" placeholder="Your name"/></div>
        <div class="form-group"><label>Age</label><input type="number" id="pAge" value="${existing.age||''}" min="10" max="100" placeholder="Age"/></div>
        <div class="form-group"><label>Weight (kg)</label><input type="number" id="pWeight" value="${existing.weight_kg||''}" step="0.1" placeholder="e.g. 65"/></div>
        <div class="form-group"><label>Height (cm)</label><input type="number" id="pHeight" value="${existing.height_cm||''}" step="0.5" placeholder="e.g. 170"/></div>
        <div class="form-group"><label>Activity Level</label><select id="pActivity">${actOpts}</select></div>
        <div class="form-group"><label>Fitness Level</label><select id="pFitness">${fitOpts}</select></div>
      </div>
    </div>
  </div>

  <div class="page-section">
    <p class="section-title">Diet Preferences</p>
    <div class="card">
      <div style="display:flex;flex-wrap:wrap;gap:9px">
        ${allDiets.map(d=>`<label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;padding:6px 12px;background:var(--surface3);border-radius:var(--r);border:1px solid var(--border)">
          <input type="checkbox" id="diet_${d}" ${dietPrefs.includes(d)?'checked':''} style="accent-color:var(--purple)"/>
          ${CAP(d)}</label>`).join('')}
      </div>
    </div>
  </div>

  <div class="page-section">
    <p class="section-title">Wellness Goals</p>
    <div class="card">
      <div style="display:flex;flex-wrap:wrap;gap:9px">
        ${allGoals.map(g=>`<label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;padding:6px 12px;background:var(--surface3);border-radius:var(--r);border:1px solid var(--border)">
          <input type="checkbox" id="goal_${g.replace(/ /g,'_')}" ${wellnessGoals.includes(g)?'checked':''} style="accent-color:var(--purple)"/>
          ${CAP(g)}</label>`).join('')}
      </div>
    </div>
  </div>

  <div class="page-section">
    <div class="card" style="background:var(--surface3)">
      <div style="font-size:12px;color:var(--muted);margin-bottom:12px;line-height:1.6">
        Your profile helps MindMate personalise workout plans, meal suggestions, and wellness coaching specifically for you.
        No data is shared externally.
      </div>
      <button class="btn btn-primary" id="saveProfileBtn">💾 Save Profile</button>
      <span id="profileStatus" style="margin-left:12px;font-size:13px;color:var(--muted)"></span>
    </div>
  </div>

  <div class="page-section">
    <p class="section-title">Account Info</p>
    <div class="card">
      <div style="display:flex;flex-direction:column;gap:8px;font-size:13.5px;color:var(--muted)">
        <div>👤 User ID: <code style="color:var(--purple-h)">${USER_ID}</code></div>
        <div>📅 Member since: <span style="color:var(--text)">${existing.created_at ? new Date(existing.created_at).toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}) : 'Today'}</span></div>
      </div>
    </div>
  </div>`;

  document.getElementById('saveProfileBtn').addEventListener('click', async () => {
    const btn = document.getElementById('saveProfileBtn');
    const status = document.getElementById('profileStatus');
    btn.disabled = true; btn.textContent = 'Saving…';
    const selectedDiets = allDiets.filter(d => document.getElementById(`diet_${d}`)?.checked);
    const selectedGoals = allGoals.filter(g => document.getElementById(`goal_${g.replace(/ /g,'_')}`)?.checked);
    try {
      await apiPost(`/user/${USER_ID}`, {
        name: document.getElementById('pName').value || 'Student',
        age: +document.getElementById('pAge').value || null,
        weight_kg: +document.getElementById('pWeight').value || null,
        height_cm: +document.getElementById('pHeight').value || null,
        activity_level: document.getElementById('pActivity').value,
        fitness_level: document.getElementById('pFitness').value,
        diet_prefs: selectedDiets,
        wellness_goals: selectedGoals,
      });
      toast('Profile saved ✓');
      status.textContent = 'Saved!'; status.style.color = 'var(--green)';
      setTimeout(() => { status.textContent = ''; }, 3000);
    } catch(e) {
      toast(e.message, 'error');
      status.textContent = 'Error saving.'; status.style.color = 'var(--red)';
    }
    btn.disabled = false; btn.textContent = '💾 Save Profile';
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
pollHealth();
// Fast-poll on startup until AI is ready, then slow down to 15s
let _fastPoll = setInterval(async () => {
  await pollHealth();
  if (mlReady) { clearInterval(_fastPoll); setInterval(pollHealth, 15000); }
}, 4000);
navigateTo('dashboard');
