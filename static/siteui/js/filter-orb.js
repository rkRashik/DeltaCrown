/* DeltaCrown — Filter Orb (accessible)
 * - Click/Enter/Space to open
 * - Hover-friendly (does not trap you)
 * - Focus trap while open
 * - Esc or backdrop click to close
 * - Restores focus to the trigger
 * - Respects prefers-reduced-motion
 */
(function () {
  const mqReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  const d = document;

  function $(sel, root) { return (root || d).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || d).querySelectorAll(sel)); }

  const state = {
    open: false,
    trapNodes: null,
    lastFocused: null,
    root: null,
    trigger: null,
    panel: null,
    backdrop: null
  };

  function init() {
    // Expect structure injected by templates/partials/_filter_orb.html:
    // <div class="filter-orb" data-orb>
    //   <button class="orb-trigger" data-orb-trigger aria-haspopup="dialog" aria-expanded="false" aria-controls="orb-panel">Filters</button>
    //   <div class="orb-backdrop" data-orb-backdrop hidden></div>
    //   <div id="orb-panel" class="orb-panel" data-orb-panel role="dialog" aria-modal="true" tabindex="-1" hidden> ... </div>
    // </div>
    const root = $('[data-orb]');
    if (!root) return;

    state.root = root;
    state.trigger = $('[data-orb-trigger]', root);
    state.panel = $('[data-orb-panel]', root);
    state.backdrop = $('[data-orb-backdrop]', root);

    if (!state.trigger || !state.panel) return;

    state.trigger.addEventListener('click', onTrigger);
    state.trigger.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onTrigger();
      }
    });

    // Hover open (non-blocking)
    root.addEventListener('mouseenter', () => {
      if (mqReduced?.matches) return; // avoid surprise openings
      open();
    });
    root.addEventListener('mouseleave', () => {
      if (mqReduced?.matches) return;
      // small delay to avoid flicker
      setTimeout(() => { if (!root.matches(':hover')) close(); }, 120);
    });

    state.backdrop && state.backdrop.addEventListener('click', close);
    d.addEventListener('keydown', onDocKeydown, true);

    // Expose a small control API
    window.DCFilterOrb = {
      open, close, toggle,
      isOpen: () => state.open
    };
  }

  function onTrigger() { toggle(); }

  function toggle() { (state.open ? close : open)(); }

  function open() {
    if (state.open) return;
    state.open = true;
    state.lastFocused = d.activeElement;

    // Make visible
    if (state.backdrop) state.backdrop.hidden = false;
    state.panel.hidden = false;

    state.trigger.setAttribute('aria-expanded', 'true');
    state.panel.setAttribute('aria-hidden', 'false');

    // Focus trap setup
    state.trapNodes = findFocusable(state.panel);
    // Focus the first tabbable or the panel itself
    (state.trapNodes[0] || state.panel).focus({ preventScroll: true });

    // Animate gently unless reduced motion
    if (!mqReduced?.matches) {
      state.panel.classList.add('is-entering');
      requestAnimationFrame(() => {
        state.panel.classList.add('is-open');
        state.panel.addEventListener('animationend', () => {
          state.panel.classList.remove('is-entering');
        }, { once: true });
      });
      state.backdrop && state.backdrop.classList.add('is-open');
    } else {
      state.panel.classList.add('is-open');
      state.backdrop && state.backdrop.classList.add('is-open');
    }
  }

  function close() {
    if (!state.open) return;
    state.open = false;

    state.trigger.setAttribute('aria-expanded', 'false');
    state.panel.setAttribute('aria-hidden', 'true');

    const finish = () => {
      state.panel.hidden = true;
      state.backdrop && (state.backdrop.hidden = true);
      // Restore focus
      if (state.lastFocused && typeof state.lastFocused.focus === 'function') {
        state.lastFocused.focus({ preventScroll: true });
      } else {
        state.trigger.focus({ preventScroll: true });
      }
    };

    if (!mqReduced?.matches) {
      state.panel.classList.add('is-leaving');
      state.panel.classList.remove('is-open');
      state.backdrop && state.backdrop.classList.remove('is-open');

      state.panel.addEventListener('animationend', () => {
        state.panel.classList.remove('is-leaving');
        finish();
      }, { once: true });
    } else {
      state.panel.classList.remove('is-open');
      state.backdrop && state.backdrop.classList.remove('is-open');
      finish();
    }
  }

  function onDocKeydown(e) {
    if (!state.open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === 'Tab') {
      // Focus trap
      const nodes = state.trapNodes || findFocusable(state.panel);
      if (!nodes.length) {
        e.preventDefault();
        state.panel.focus();
        return;
      }
      const idx = nodes.indexOf(d.activeElement);
      if (e.shiftKey) {
        if (idx <= 0) {
          e.preventDefault();
          nodes[nodes.length - 1].focus();
        }
      } else {
        if (idx === nodes.length - 1) {
          e.preventDefault();
          nodes[0].focus();
        }
      }
    }
  }

  function findFocusable(scope) {
    const sel = [
      'a[href]:not([tabindex="-1"])',
      'area[href]:not([tabindex="-1"])',
      'button:not([disabled]):not([tabindex="-1"])',
      'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
      'select:not([disabled]):not([tabindex="-1"])',
      'textarea:not([disabled]):not([tabindex="-1"])',
      '[tabindex]:not([tabindex="-1"])'
    ].join(',');
    return $all(sel, scope).filter(el => el.offsetParent !== null);
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
