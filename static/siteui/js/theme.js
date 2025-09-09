(function () {
  var STORAGE_KEY = 'dc.theme.v1';
  var btn = null;
  var statusEl = null;
  var mql = null;

  function currentSavedMode() {
    try { return localStorage.getItem(STORAGE_KEY) || 'system'; }
    catch (e) { return 'system'; }
  }

  function apply(mode) {
    // mode: 'light' | 'dark' | 'system'
    var effective = mode;
    if (mode === 'system') {
      var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      effective = prefersDark ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', effective);
    document.documentElement.setAttribute('data-theme-mode', mode);
    if (btn) {
      btn.dataset.state = mode;
      setIcons(mode);
      setAria(mode);
    }
  }

  function setIcons(mode) {
    var icons = {
      system: document.querySelector('[data-icon="system"]'),
      light:  document.querySelector('[data-icon="light"]'),
      dark:   document.querySelector('[data-icon="dark"]'),
    };
    if (!icons.system || !icons.light || !icons.dark) return;
    icons.system.classList.add('hidden');
    icons.light.classList.add('hidden');
    icons.dark.classList.add('hidden');
    icons[mode].classList.remove('hidden');
  }

  function setAria(mode) {
    if (statusEl) {
      statusEl.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
    }
    if (btn) {
      btn.setAttribute('aria-label', 'Toggle color theme (current: ' + mode + ')');
      // Use aria-pressed to indicate non-system binary states as a hint:
      btn.setAttribute('aria-pressed', mode === 'dark' || mode === 'light' ? 'true' : 'false');
    }
  }

  function save(mode) {
    try { localStorage.setItem(STORAGE_KEY, mode); } catch (e) {}
  }

  function cycle(from) {
    // system -> light -> dark -> system
    if (from === 'system') return 'light';
    if (from === 'light')  return 'dark';
    return 'system';
  }

  function onClick() {
    var prev = currentSavedMode();
    var next = cycle(prev);
    save(next);
    apply(next);
  }

  function onSystemChange(e) {
    var mode = currentSavedMode();
    if (mode === 'system') {
      apply('system'); // recompute effective theme
    }
  }

  function init() {
    btn = document.getElementById('theme-toggle');
    statusEl = document.getElementById('theme-toggle-status');
    if (btn) btn.addEventListener('click', onClick);

    // watch system changes
    if (window.matchMedia) {
      mql = window.matchMedia('(prefers-color-scheme: dark)');
      try {
        // Modern browsers
        mql.addEventListener('change', onSystemChange);
      } catch (err) {
        // Safari < 14
        mql.addListener(onSystemChange);
      }
    }

    // Start in the saved mode (the head inline script already applied the effective theme)
    setIcons(currentSavedMode());
    setAria(currentSavedMode());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
