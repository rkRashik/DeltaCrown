// static/src/js/theme.js
// Theme modes: 'light' | 'dark' | 'auto' (default)
// Persists in localStorage('theme'); syncs with prefers-color-scheme when auto.

(function () {
  const ROOT = document.documentElement;
  const STORAGE_KEY = 'theme';

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function apply(mode) {
    // Compute effective theme
    let effective = mode === 'auto' ? (systemPrefersDark() ? 'dark' : 'light') : mode;
    ROOT.setAttribute('data-theme', effective);
    ROOT.setAttribute('data-theme-mode', mode); // exposes whether we're in auto
    // Update toggle aria-label (if present)
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.setAttribute('aria-label', `Switch theme (current: ${effective}${mode==='auto' ? ' via auto' : ''})`);
      btn.dataset.mode = mode;
    }
  }

  function setMode(mode) {
    localStorage.setItem(STORAGE_KEY, mode);
    apply(mode);
  }

  function cycle() {
    const cur = localStorage.getItem(STORAGE_KEY) || 'auto';
    const next = cur === 'light' ? 'dark' : cur === 'dark' ? 'auto' : 'light';
    setMode(next);
  }

  // Init
  const saved = localStorage.getItem(STORAGE_KEY) || 'auto';
  apply(saved);

  // React to system changes in auto mode
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener?.('change', () => {
      if ((localStorage.getItem(STORAGE_KEY) || 'auto') === 'auto') apply('auto');
    });
  }

  // Button hookup
  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', cycle);
    }
  });
})();
