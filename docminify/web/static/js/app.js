/**
 * DocMinify — Frontend Application
 * Theme management · File upload · UI interactions
 */
(function () {
  'use strict';

  /* =========================================
     THEME MANAGEMENT
     ========================================= */
  const THEMES = ['light', 'dark', 'dim'];

  function stored()   { return localStorage.getItem('docminify-theme') || 'light'; }

  function setTheme(t) {
    if (!THEMES.includes(t)) t = 'light';
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('docminify-theme', t);
    refreshThemeIcon(t);
  }

  function cycleTheme() {
    const i = THEMES.indexOf(stored());
    setTheme(THEMES[(i + 1) % THEMES.length]);
  }

  function refreshThemeIcon(t) {
    document.querySelectorAll('.theme-icon').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.theme-icon-' + t).forEach(el => el.classList.remove('hidden'));
    document.querySelectorAll('.theme-label').forEach(el => {
      el.textContent = t.charAt(0).toUpperCase() + t.slice(1);
    });
  }

  // Apply immediately (runs before paint because script is in <head> via base.html inline)
  setTheme(stored());

  /* =========================================
     MOBILE MENU
     ========================================= */
  function initMobileMenu() {
    const btn   = document.getElementById('mobile-menu-toggle');
    const menu  = document.getElementById('mobile-menu');
    const close = document.getElementById('mobile-menu-close');
    const bg    = document.getElementById('mobile-menu-backdrop');
    if (!btn || !menu) return;

    const panel = menu.querySelector('.menu-panel');

    function open() {
      menu.classList.remove('hidden');
      requestAnimationFrame(() => panel && panel.classList.add('open'));
    }
    function shut() {
      panel && panel.classList.remove('open');
      setTimeout(() => menu.classList.add('hidden'), 300);
    }

    btn.addEventListener('click', open);
    close && close.addEventListener('click', shut);
    bg    && bg.addEventListener('click', shut);
  }

  /* =========================================
     FILE UPLOAD
     ========================================= */
  const FORMATS  = ['.pdf','.docx','.xlsx','.pptx','.txt','.zip'];
  const MAX_SIZE = 100 * 1024 * 1024; // 100 MB
  let selectedFile = null;

  function initUpload() {
    const zone  = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');
    if (!zone || !input) return;

    /* Click anywhere in zone to browse */
    zone.addEventListener('click', e => {
      if (e.target.closest('#optimize-btn') || e.target.closest('#reset-btn')) return;
      input.click();
    });

    const browseBtn = document.getElementById('browse-btn');
    if (browseBtn) browseBtn.addEventListener('click', e => { e.stopPropagation(); input.click(); });

    /* Drag & drop */
    ['dragenter','dragover'].forEach(evt =>
      zone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); zone.classList.add('drag-over'); })
    );
    ['dragleave','drop'].forEach(evt =>
      zone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); zone.classList.remove('drag-over'); })
    );
    zone.addEventListener('drop', e => {
      if (e.dataTransfer.files.length) pick(e.dataTransfer.files[0]);
    });

    /* Input change */
    input.addEventListener('change', () => { if (input.files.length) pick(input.files[0]); });

    /* Buttons */
    const optBtn = document.getElementById('optimize-btn');
    const rstBtn = document.getElementById('reset-btn');
    if (optBtn) optBtn.addEventListener('click', e => { e.stopPropagation(); upload(); });
    if (rstBtn) rstBtn.addEventListener('click', e => { e.stopPropagation(); reset(); });
  }

  function pick(file) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!FORMATS.includes(ext)) return notify('Unsupported format. Allowed: ' + FORMATS.join(', '), 'error');
    if (file.size > MAX_SIZE)     return notify('File exceeds the 100 MB limit.', 'error');

    selectedFile = file;

    const info   = document.getElementById('file-info');
    const prompt = document.getElementById('upload-prompt');
    if (!info) return;

    document.getElementById('selected-file-name').textContent = file.name;
    document.getElementById('selected-file-size').textContent = fmt(file.size);

    const badge = document.getElementById('selected-file-type');
    if (badge) {
      const t = file.name.split('.').pop().toLowerCase();
      badge.textContent = t.toUpperCase();
      badge.className = 'badge-' + t + ' text-xs font-bold px-2.5 py-1 rounded-lg';
    }

    info.classList.remove('hidden');
    prompt && prompt.classList.add('hidden');
  }

  function reset() {
    selectedFile = null;
    const ids = { 'file-info':'add', 'upload-prompt':'remove', 'result-panel':'add', 'progress-panel':'add' };
    Object.entries(ids).forEach(([id, action]) => {
      const el = document.getElementById(id);
      if (el) el.classList[action]('hidden');
    });
    const input = document.getElementById('file-input');
    if (input) input.value = '';
    const btn = document.getElementById('optimize-btn');
    if (btn) btn.disabled = false;
  }

  async function upload() {
    if (!selectedFile) return;

    const prog = document.getElementById('progress-panel');
    const btn  = document.getElementById('optimize-btn');
    if (prog) prog.classList.remove('hidden');
    if (btn)  btn.disabled = true;

    const fd = new FormData();
    fd.append('file', selectedFile);

    try {
      progress(10, 'Uploading file…');

      const res = await fetch('/optimize', { method: 'POST', body: fd });

      progress(60, 'Optimizing…');
      
      // Check for error response
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error: ${res.status}`);
      }

      progress(90, 'Preparing download…');
      const blob = await res.blob();

      progress(100, 'Complete!');
      setTimeout(() => showResult(selectedFile.size, blob.size, blob), 500);
    } catch (err) {
      console.error(err);
      notify('Optimization failed: ' + err.message, 'error');
      if (prog) prog.classList.add('hidden');
      if (btn)  btn.disabled = false;
    }
  }

  function progress(pct, msg) {
    const bar  = document.getElementById('progress-bar');
    const txt  = document.getElementById('progress-text');
    const num  = document.getElementById('progress-percent');
    if (bar) bar.style.width = pct + '%';
    if (txt) txt.textContent = msg;
    if (num) num.textContent = pct + '%';
  }

  function showResult(origSize, optSize, blob) {
    document.getElementById('progress-panel')?.classList.add('hidden');
    const panel = document.getElementById('result-panel');
    if (panel) panel.classList.remove('hidden');

    const saved = origSize - optSize;
    const pct   = origSize > 0 ? (saved / origSize) * 100 : 0;

    setText('original-size',  fmt(origSize));
    setText('optimized-size', fmt(optSize));
    setText('savings-percent', pct.toFixed(1) + '%');
    setText('savings-amount',  fmt(Math.abs(saved)));

    /* Animate SVG ring */
    const circle = document.getElementById('progress-circle');
    if (circle) {
      const C = 2 * Math.PI * 54;                       // circumference
      circle.style.strokeDasharray  = C;
      circle.style.strokeDashoffset = C;
      requestAnimationFrame(() => {
        circle.style.transition = 'stroke-dashoffset 1.5s ease';
        circle.style.strokeDashoffset = C - (pct / 100) * C;
      });
    }

    /* Download button */
    const dl = document.getElementById('download-btn');
    if (dl) {
      dl.onclick = () => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'optimized_' + (selectedFile ? selectedFile.name : 'file');
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);
      };
    }
  }

  /* =========================================
     NOTIFICATIONS
     ========================================= */
  function notify(msg, type) {
    type = type || 'info';
    const box = document.getElementById('notification-container');
    if (!box) return;

    const colors = {
      info:    { bg: 'var(--accent-light)',  fg: 'var(--accent)' },
      success: { bg: 'var(--success-light)', fg: 'var(--success)' },
      error:   { bg: 'var(--danger-light)',  fg: 'var(--danger)' },
      warning: { bg: 'var(--warning-light)', fg: 'var(--warning)' }
    };
    const c = colors[type] || colors.info;

    const el = document.createElement('div');
    el.className = 'animate-slide-down';
    Object.assign(el.style, {
      backgroundColor: c.bg, color: c.fg,
      padding: '12px 20px', borderRadius: '14px', marginBottom: '8px',
      fontSize: '14px', fontWeight: '500',
      boxShadow: '0 4px 14px var(--shadow)',
      transition: 'all .3s ease'
    });
    el.textContent = msg;
    box.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(-10px)';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  }

  /* =========================================
     SMOOTH SCROLL
     ========================================= */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', e => {
        const target = document.querySelector(a.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
  }

  /* =========================================
     HELPERS
     ========================================= */
  function fmt(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024, u = ['B','KB','MB','GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + u[i];
  }

  function setText(id, v) {
    const el = document.getElementById(id);
    if (el) el.textContent = v;
  }

  /* =========================================
     INIT
     ========================================= */
  document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initUpload();
    initSmoothScroll();

    // Theme toggles (desktop + mobile)
    ['theme-toggle', 'mobile-theme-toggle'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', cycleTheme);
    });

    // Account-page theme buttons
    document.querySelectorAll('[data-set-theme]').forEach(btn => {
      btn.addEventListener('click', () => setTheme(btn.dataset.setTheme));
    });

    // Re-apply icon state in case DOM loaded after first setTheme call
    refreshThemeIcon(stored());
  });

  /* Public API */
  window.DocMinify = { setTheme, cycleTheme, notify, fmt };
})();
