/* =====================================================================
   AI Employees page — renders the gallery and the hash-routed detail
   view. Static, no build step, no framework. Just the DOM.
   ===================================================================== */

const galleryEl = document.getElementById('employee-gallery');
const detailEl  = document.getElementById('employee-detail');
const galleryWrap = document.getElementById('gallery-wrap');

/* ---------- Build the gallery cards ---------- */
function renderGallery() {
  galleryEl.innerHTML = EMPLOYEES.map((e) => `
    <article class="emp-card" data-id="${e.id}" tabindex="0" role="button"
             aria-label="Meet ${e.name}, the ${e.role}">
      <div class="emp-avatar">${ICONS[e.icon]}</div>
      <div class="emp-role">${e.role}</div>
      <h3>${e.name}</h3>
      <p class="emp-does">${e.does}</p>
      <div class="emp-meet">
        <span class="btn-ghost">Meet ${e.name} <span class="arrow">&rarr;</span></span>
      </div>
    </article>
  `).join('');

  galleryEl.querySelectorAll('.emp-card').forEach((card) => {
    const go = () => { location.hash = card.dataset.id; };
    card.addEventListener('click', go);
    card.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(); }
    });
  });
}

/* ---------- Build a single detail view ---------- */
function renderDetail(emp) {
  detailEl.innerHTML = `
    <a class="back-link" href="#"><span>&larr;</span> All AI Employees</a>

    <div class="detail-head">
      <div class="detail-avatar">${ICONS[emp.icon]}</div>
      <div class="detail-titles">
        <div class="emp-role">${emp.role}</div>
        <h1>${emp.name}</h1>
        <p class="tagline">${emp.tagline}</p>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-main">
        <div class="detail-panel">
          <h4>The ready-to-paste prompt</h4>
          <div class="prompt-box">
            <span class="prompt-label">Copy &amp; paste into ChatGPT, Claude, or Gemini</span>
            <button class="copy-button" type="button">Copy</button>
            <div class="prompt-text">${escapeHtml(emp.prompt)}</div>
          </div>
          <div class="fid-note">
            <div class="t">You stay the fiduciary.</div>
            <p>${emp.fiduciary}</p>
          </div>
        </div>
      </div>

      <aside class="detail-side">
        <div class="detail-panel">
          <h4>What ${emp.name} does for you</h4>
          <p style="color:var(--text-muted);font-size:0.93rem;margin-bottom:18px;">${emp.does}</p>
          <h4 style="margin-top:6px;">You'll walk away with</h4>
          <ul>${emp.delivers.map((d) => `<li>${d}</li>`).join('')}</ul>
        </div>
        <div class="detail-panel">
          <h4>Best for</h4>
          <div class="tag-row">
            ${emp.bestFor.map((b) => `<span class="chip">${b}</span>`).join('')}
          </div>
        </div>
      </aside>
    </div>
  `;

  // Copy button
  const btn = detailEl.querySelector('.copy-button');
  btn.addEventListener('click', () => {
    navigator.clipboard.writeText(emp.prompt).then(() => {
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1900);
    }).catch(() => {
      // Fallback for older browsers / file:// edge cases
      const ta = document.createElement('textarea');
      ta.value = emp.prompt; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); btn.textContent = 'Copied!'; btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1900); }
      finally { document.body.removeChild(ta); }
    });
  });
}

/* ---------- Router ---------- */
function route() {
  const id = location.hash.replace('#', '');
  const emp = EMPLOYEES.find((e) => e.id === id);

  if (emp) {
    renderDetail(emp);
    galleryWrap.style.display = 'none';
    detailEl.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
    document.title = `${emp.name} — ${emp.role} · The Realtor's AIME`;
  } else {
    detailEl.classList.remove('active');
    detailEl.innerHTML = '';
    galleryWrap.style.display = 'block';
    document.title = "AI Employees · The Realtor's AIME";
  }
}

/* ---------- Util ---------- */
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/* ---------- Init ---------- */
renderGallery();
window.addEventListener('hashchange', route);
route();
