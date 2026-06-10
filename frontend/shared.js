/* ── Shared utilities ─────────────────────────────────────────────── */
const API = '';   // same origin

function toast(msg, type = 'info') {
  let c = document.getElementById('toast-container');
  if (!c) { c = document.createElement('div'); c.id = 'toast-container'; document.body.appendChild(c); }
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function getToken() { return localStorage.getItem('token'); }
function getUser()  {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); }
  catch { return null; }
}
function logout() { localStorage.clear(); location.href = '/frontend/index.html'; }

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers['Content-Type'];
  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 401) { logout(); return null; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast(data.detail || 'Request failed', 'error'); throw new Error(data.detail); }
  return data;
}

function badgeStatus(status) {
  const m = { cleared:'success', approved:'success', in_progress:'info',
               pending:'warning', rejected:'danger', skipped:'warning' };
  return `<span class="badge badge-${m[status]||'info'}">${status.replace('_',' ')}</span>`;
}

function riskColor(score) {
  if (score < 30)  return '#27ae8f';
  if (score < 60)  return '#e8a020';
  return '#c0392b';
}

function avatarInitials(name) {
  return (name || '?').split(' ').slice(0,2).map(w => w[0]).join('').toUpperCase();
}

// Route guard
function requireAuth(role) {
  const user = getUser();
  if (!user || !getToken()) { location.href = '/frontend/index.html'; return false; }
  if (role && user.role !== role) { toast('Access denied', 'error');
    location.href = '/frontend/index.html'; return false; }
  return true;
}
