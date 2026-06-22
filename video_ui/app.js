// AIME Video UI — app.js
// Change this to your deployed API endpoint when live:
const API_URL = '/create-video';

const HISTORY_KEY = 'aime_video_history';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const promptEl  = document.getElementById('prompt');
const durationEl = document.getElementById('duration');
const aspectEl  = document.getElementById('aspect');
const createBtn = document.getElementById('createBtn');
const spinner   = document.getElementById('spinner');
const statusEl  = document.getElementById('status');
const resultEl  = document.getElementById('result');
const videoEl   = document.getElementById('videoPlayer');
const downloadEl = document.getElementById('downloadBtn');

// ── Status helpers ─────────────────────────────────────────────────────────────
function setStatus(msg, type = '') {
  statusEl.textContent = msg;
  statusEl.className = type;
}

function setLoading(on) {
  createBtn.disabled = on;
  spinner.classList.toggle('show', on);
  if (!on) setStatus('');
}

// ── Main: create video ─────────────────────────────────────────────────────────
async function createVideo() {
  const prompt = promptEl.value.trim();
  if (!prompt) { setStatus('Enter a topic first.', 'error'); return; }

  setLoading(true);
  resultEl.classList.remove('show');
  setStatus('Generating scene content with Claude…');

  const steps = [
    [2000,  'Building HyperFrames composition…'],
    [8000,  'Rendering video (this takes ~20–30s)…'],
    [20000, 'Encoding and uploading…'],
  ];
  const timers = steps.map(([delay, msg]) => setTimeout(() => setStatus(msg), delay));

  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        duration: parseInt(durationEl.value),
        aspect: aspectEl.value,
      }),
    });

    timers.forEach(clearTimeout);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Unknown error');
    }

    const data = await res.json();
    showResult(data.url, prompt);
    saveHistory(data.video_id, prompt, data.url);
    setStatus('Done!', 'success');

  } catch (e) {
    timers.forEach(clearTimeout);
    setStatus('Error: ' + e.message, 'error');
  } finally {
    setLoading(false);
  }
}

// ── Show the video ─────────────────────────────────────────────────────────────
function showResult(url, prompt) {
  videoEl.src = url;
  downloadEl.href = url;
  downloadEl.download = `aime-${prompt.slice(0,30).replace(/\W+/g,'-')}.mp4`;
  resultEl.classList.add('show');
  resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Reset form ─────────────────────────────────────────────────────────────────
function resetForm() {
  promptEl.value = '';
  resultEl.classList.remove('show');
  videoEl.src = '';
  setStatus('');
  promptEl.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── History ────────────────────────────────────────────────────────────────────
function saveHistory(videoId, prompt, url) {
  const history = getHistory();
  history.unshift({ videoId, prompt, url, ts: Date.now() });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 20)));
  renderHistory();
}

function getHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function renderHistory() {
  const history = getHistory();
  const el = document.getElementById('history');
  if (!history.length) { el.innerHTML = ''; return; }

  const fmt = ts => {
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  };

  el.innerHTML = `<div class="history-title">Recent Videos</div>` +
    history.map(h => `
      <div class="history-item" onclick="showResult('${h.url}','${h.prompt.replace(/'/g,"\\'")}')">
        <div class="dot"></div>
        <div class="label">${h.prompt.slice(0, 55)}${h.prompt.length > 55 ? '…' : ''}</div>
        <div class="time">${fmt(h.ts)}</div>
      </div>
    `).join('');
}

// Allow Cmd/Ctrl+Enter to submit
promptEl.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') createVideo();
});

// Load history on page start
renderHistory();
