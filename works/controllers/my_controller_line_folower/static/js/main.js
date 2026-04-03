// ── State ────────────────────────────────────────────
let selectedZone = null;
let selectedPriority = 'ODDIY';

const ZONE_LABELS = { B:'Saqlash zonasi', C:'Ishlov zonasi', D:'Chiqish zonasi' };
const ZONE_CLASS  = { B:'zone-b', C:'zone-c', D:'zone-d' };
const PRIO_TEXT   = { YUQORI:'Yuqori', ODDIY:'Oddiy', PAST:'Past' };
const PRIO_CLASS  = { YUQORI:'high', ODDIY:'mid', PAST:'low' };

const STATE_MAP = {
  'IDLE':          { text:'KUTMOQDA',        moving:false },
  'idle':          { text:'KUTMOQDA',        moving:false },
  'going_to_dest': { text:'YETKAZMOQDA',     moving:true  },
  'waiting':       { text:'YUKLANMOQDA',     moving:false },
  'going_to_A':    { text:'QAYTMOQDA',       moving:true  },
  'waiting_at_A':  { text:'BAZADA KUTMOQDA', moving:false },
};

// minimap robot pozitsiyalari (top%, left%)
const MM_POS = {
  A:          { top:'50%', left:'18%' },
  B:          { top:'15%', left:'78%' },
  C:          { top:'50%', left:'78%' },
  D:          { top:'82%', left:'78%' },
  going_to_A: { top:'50%', left:'50%' },
};

// ── Clock ────────────────────────────────────────────
function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('uz-UZ');
}
setInterval(updateClock, 1000);
updateClock();

// ── Priority select ──────────────────────────────────
function setPriority(p) {
  selectedPriority = p;
  document.querySelectorAll('.prio-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.p === p);
  });
}

// ── Zone select ──────────────────────────────────────
function selectZone(key) {
  selectedZone = key;
  document.querySelectorAll('.zone-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('zcard-' + key).classList.add('selected');

  const info = document.getElementById('selected-info');
  info.textContent = '→ ' + ZONE_LABELS[key] + ' tanlandi';
  info.className = 'selected-info ready';

  const btn = document.getElementById('btn-submit');
  btn.classList.add('ready');
}

// ── Submit ───────────────────────────────────────────
async function submitOrder() {
  if (!selectedZone) return;
  const cargo = document.getElementById('cargo-input').value.trim() || 'Yuk';
  const btn = document.getElementById('btn-submit');
  btn.textContent = 'Yuborilmoqda...';
  btn.classList.remove('ready');

  try {
    const res = await fetch('/api/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dest: selectedZone, cargo, priority: selectedPriority }),
    });
    if (res.ok) {
      document.getElementById('cargo-input').value = '';
      // Reset zone selection
      document.querySelectorAll('.zone-card').forEach(c => c.classList.remove('selected'));
      document.getElementById('selected-info').textContent = 'Zona tanlanmagan';
      document.getElementById('selected-info').className = 'selected-info';
      selectedZone = null;
      await refresh();
    }
  } finally {
    btn.textContent = 'Buyurtma berish →';
  }
}

// ── Delete ───────────────────────────────────────────
async function deleteOrder(id) {
  await fetch('/api/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  });
  await refresh();
}

// ── Clear all ────────────────────────────────────────
async function clearAll() {
  if (!confirm("Barcha buyurtmalarni o'chirasizmi?")) return;
  await fetch('/api/clear', { method: 'POST' });
  await refresh();
}

// ── Render queue table ───────────────────────────────
function renderQueue(orders) {
  const body = document.getElementById('qt-body');
  document.getElementById('total-badge').textContent = orders.length + ' ta';

  if (orders.length === 0) {
    body.innerHTML = `<div class="qt-empty"><div class="qte-icon">📦</div><div>Navbat bo'sh — buyurtma qo'shing</div></div>`;
    return;
  }

  body.innerHTML = orders.map((o, i) => {
    const prioClass = PRIO_CLASS[o.priority] || 'mid';
    const zoneClass = ZONE_CLASS[o.dest] || '';
    return `
    <div class="qt-row${i === 0 ? ' first-row' : ''}">
      <span class="qt-id">#${o.id}</span>
      <span class="qt-cargo" title="${o.cargo}">${o.cargo}</span>
      <span><span class="qt-zone ${zoneClass}">${o.dest} — ${o.dest === 'B' ? 'Saqlash' : o.dest === 'C' ? 'Ishlov' : 'Chiqish'}</span></span>
      <span class="qt-prio">
        <span class="prio-ind ${prioClass}"></span>
        ${PRIO_TEXT[o.priority] || o.priority}
      </span>
      <span class="qt-time">${o.created || '—'}</span>
      <button class="qt-del" onclick="deleteOrder('${o.id}')" title="O'chirish">✕</button>
    </div>`;
  }).join('');
}

// ── Render zone stats ────────────────────────────────
function renderZoneStats(orders, stats) {
  ['B','C','D'].forEach(k => {
    const n = stats[k] || 0;
    // Topbar pills
    const zp = document.getElementById('zp-' + k);
    if (zp) {
      zp.classList.toggle('has-orders', n > 0);
      const cnt = zp.querySelector('.zp-count');
      if (cnt) cnt.textContent = n;
    }
    // Topbar count
    const zpCount = document.getElementById('zp-count-' + k);
    if (zpCount) zpCount.textContent = n;
    // Zone card queues
    const qel = document.getElementById('zc-queue-' + k);
    if (qel) {
      qel.textContent = n + ' ta';
      qel.className = 'zc-queue' + (n > 0 ? ' busy' : '');
    }
  });

  // High priority count
  const highCount = orders.filter(o => o.priority === 'YUQORI').length;
  const rmHigh = document.getElementById('rm-high');
  if (rmHigh) {
    rmHigh.textContent = highCount;
    rmHigh.className = 'rm-val' + (highCount > 0 ? ' high' : '');
  }
}

// ── Render robot ─────────────────────────────────────
function renderRobot(data) {
  const info = STATE_MAP[data.state] || { text: data.state, moving: false };
  const { moving } = info;

  // Online dot
  const dot = document.getElementById('sys-dot');
  const txt = document.getElementById('sys-text');
  if (dot) dot.className = 'status-dot ' + (data.online ? 'online' : 'offline');
  if (txt) txt.textContent = data.online ? 'Online' : 'Offline';

  // Robot body animation
  const body = document.querySelector('.robot-body');
  const eyes = document.querySelectorAll('.robot-eye');
  const mouth = document.getElementById('robot-mouth');
  const wheels = document.querySelectorAll('.robot-wheel');

  if (body) {
    body.className = 'robot-body' + (moving ? ' moving' : '') + (data.state === 'waiting' ? ' delivering' : '');
  }
  eyes.forEach(e => e.classList.toggle('active', moving));
  if (mouth) mouth.className = 'robot-mouth' + (data.state === 'waiting_at_A' || data.state === 'IDLE' ? ' happy' : '');
  wheels.forEach(w => w.classList.toggle('spin', moving));

  // State text
  const riState = document.getElementById('ri-state');
  if (riState) {
    riState.textContent = info.text;
    riState.className = 'ri-state' + (moving ? ' active' : '');
  }

  const riDest = document.getElementById('ri-dest');
  if (riDest) {
    const destNames = { B:'B — Saqlash', C:'C — Ishlov', D:'D — Chiqish', A:'A — Qabul (baza)' };
    riDest.textContent = data.current ? (destNames[data.current] || data.current) : '—';
  }

  // Metrics
  const rmQ = document.getElementById('rm-queue');
  const rmD = document.getElementById('rm-done');
  if (rmQ) rmQ.textContent = data.orders.length;
  if (rmD) rmD.textContent = data.completed;

  // Minimap robot position
  const mmRobot = document.getElementById('mm-robot');
  if (mmRobot) {
    let pos = MM_POS['A'];
    if (data.current && MM_POS[data.current]) pos = MM_POS[data.current];
    else if (moving) pos = MM_POS['going_to_A'];
    mmRobot.style.top = pos.top;
    mmRobot.style.left = pos.left;
  }

  // Minimap zone highlights
  ['A','B','C','D'].forEach(z => {
    const el = document.getElementById('mm-' + z.toLowerCase());
    if (el) el.classList.toggle('active-zone', data.current === z);
  });
}

// ── Render log ───────────────────────────────────────
function renderLog(log) {
  const el = document.getElementById('log-stream');
  if (!log || log.length === 0) {
    el.innerHTML = '<div class="log-empty">Yozuv yo\'q...</div>';
    return;
  }
  el.innerHTML = log.map(e => `
    <div class="log-entry">
      <span class="le-time">${e.time}</span>
      <span class="le-dot ${e.level || 'info'}"></span>
      <span class="le-msg">${e.msg}</span>
    </div>
  `).join('');
}

// ── Main refresh ─────────────────────────────────────
async function refresh() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    renderQueue(data.orders);
    renderZoneStats(data.orders, data.stats || {});
    renderRobot(data);
    renderLog(data.log);
  } catch (e) {
    console.warn('Refresh error:', e);
  }
}

refresh();
setInterval(refresh, 1500);