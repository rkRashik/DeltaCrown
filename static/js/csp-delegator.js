/**
 * CSP-Safe Event Delegator — DeltaCrown
 *
 * Replaces inline event handlers (onclick, onchange, oninput, onkeyup, etc.)
 * with data-attribute-based delegation for Content Security Policy compliance.
 *
 * CLICK:
 *   data-click="Namespace.method"             → calls window.Namespace.method()
 *   data-click-args='["arg1",2]'              → passes JSON-parsed arguments
 *   data-click-self="Namespace.method"        → fires only if event.target === element
 *   data-click-hide="elementId"               → adds 'hidden' class to #elementId
 *   data-click-show="elementId"               → removes 'hidden' class from #elementId
 *   data-click-toggle="elementId"             → toggles 'hidden' on #elementId
 *   data-click-href="url"                     → navigates to url
 *   data-click-pass-el                        → appends element as last arg
 *   data-click-json='{"key":"val"}'           → passes parsed JSON as single arg
 *   data-click-also="Namespace.method"        → calls second function after primary
 *   data-click-also-args='["arg"]'            → arguments for data-click-also
 *
 * CHANGE:
 *   data-change="Namespace.method"            → calls on change event
 *   data-change-args='["arg1"]'               → additional arguments
 *   data-change-pass="value"                  → appends element.value as last arg
 *   data-change-pass="checked"                → appends element.checked as last arg
 *   data-change-pass="el"                     → appends element reference as last arg
 *
 * INPUT:
 *   data-input="Namespace.method"             → calls on input event
 *   data-input-args='["arg1"]'                → additional arguments
 *   data-input-pass="value"                   → appends element.value as last arg
 *
 * KEYUP:
 *   data-keyup="Namespace.method"             → calls on keyup event
 *
 * SUBMIT:
 *   data-submit-action="Namespace.method"     → calls on form submit (preventDefault)
 *
 * IMAGE FALLBACK:
 *   data-fallback-src="/path/to/fallback.png" → sets src on error
 *   data-fallback="hide"                      → hides element on error
 *
 * MISC:
 *   data-stop-propagation                     → calls event.stopPropagation()
 */
(function() {
  'use strict';

  /**
   * Resolve a dotted path (e.g. "TOC.matches.refresh") to a function on window.
   */
  function resolve(path) {
    var parts = path.split('.');
    var obj = window;
    for (var i = 0; i < parts.length; i++) {
      if (obj == null) return null;
      obj = obj[parts[i]];
    }
    return typeof obj === 'function' ? obj : null;
  }

  /**
   * Parse JSON args from a data attribute. Returns array.
   */
  function parseArgs(raw) {
    if (!raw) return [];
    try { return JSON.parse(raw); }
    catch (e) { return [raw]; }
  }

  /**
   * Append pass-through value to args array based on data-*-pass attribute.
   */
  function appendPass(el, passAttr, args) {
    if (!passAttr) return args;
    var copy = args.slice();
    if (passAttr === 'value') copy.push(el.value);
    else if (passAttr === 'checked') copy.push(el.checked);
    else if (passAttr === 'el') copy.push(el);
    else copy.push(el[passAttr]);
    return copy;
  }

  // ── CLICK delegation ──────────────────────────────────────────────
  document.addEventListener('click', function(e) {
    var t = e.target;

    // data-stop-propagation
    if (t.closest('[data-stop-propagation]')) {
      e.stopPropagation();
    }

    // data-click-self — backdrop dismiss (only fires when target is the element itself)
    if (t.hasAttribute && t.hasAttribute('data-click-self')) {
      var fn = resolve(t.getAttribute('data-click-self'));
      if (fn) {
        var selfArgs = parseArgs(t.getAttribute('data-click-args'));
        fn.apply(null, selfArgs);
      }
      return;
    }

    // data-click-hide
    var hideEl = t.closest('[data-click-hide]');
    if (hideEl) {
      var target = document.getElementById(hideEl.getAttribute('data-click-hide'));
      if (target) target.classList.add('hidden');
      return;
    }

    // data-click-show
    var showEl = t.closest('[data-click-show]');
    if (showEl) {
      target = document.getElementById(showEl.getAttribute('data-click-show'));
      if (target) target.classList.remove('hidden');
      return;
    }

    // data-click-toggle
    var toggleEl = t.closest('[data-click-toggle]');
    if (toggleEl) {
      target = document.getElementById(toggleEl.getAttribute('data-click-toggle'));
      if (target) target.classList.toggle('hidden');
      return;
    }

    // data-click-href
    var hrefEl = t.closest('[data-click-href]');
    if (hrefEl) {
      window.location.href = hrefEl.getAttribute('data-click-href');
      return;
    }

    // data-click-search (window.location.search = value)
    var searchEl = t.closest('[data-click-search]');
    if (searchEl) {
      window.location.search = searchEl.getAttribute('data-click-search');
      return;
    }

    // data-click-trigger (click another element by ID)
    var triggerEl = t.closest('[data-click-trigger]');
    if (triggerEl) {
      var trigTarget = document.getElementById(triggerEl.getAttribute('data-click-trigger'));
      if (trigTarget) trigTarget.click();
      return;
    }

    // data-click-copy (copy text to clipboard)
    var copyEl = t.closest('[data-click-copy]');
    if (copyEl) {
      var copyExpr = copyEl.getAttribute('data-click-copy');
      var text = copyExpr === 'window.location.href' ? window.location.href : copyExpr;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
          if (window.showToast) window.showToast({type:'success', message:'Link copied to clipboard!'});
        });
      }
      return;
    }

    // data-click-child (click a child element matching selector)
    var childClickEl = t.closest('[data-click-child]');
    if (childClickEl) {
      var child = childClickEl.querySelector(childClickEl.getAttribute('data-click-child'));
      if (child) child.click();
      return;
    }

    // data-click-query (click an element matching a document-level selector)
    var queryClickEl = t.closest('[data-click-query]');
    if (queryClickEl) {
      var qTarget = document.querySelector(queryClickEl.getAttribute('data-click-query'));
      if (qTarget) qTarget.click();
      return;
    }

    // data-click-dismiss-parent (remove parent element)
    var dismissEl = t.closest('[data-click-dismiss-parent]');
    if (dismissEl) {
      var parent = dismissEl.parentElement;
      if (parent) parent.remove();
      return;
    }

    // data-click-toggle-child (toggle hidden on a child within closest ancestor)
    var toggleChildEl = t.closest('[data-click-toggle-child]');
    if (toggleChildEl) {
      var selector = toggleChildEl.getAttribute('data-click-toggle-child');
      var parent = toggleChildEl.parentElement;
      while (parent) {
        var tgt = parent.querySelector(selector);
        if (tgt) { tgt.classList.toggle('hidden'); break; }
        parent = parent.parentElement;
      }
      return;
    }

    // data-click (general method call)
    var clickEl = t.closest('[data-click]');
    if (clickEl) {
      fn = resolve(clickEl.getAttribute('data-click'));
      if (fn) {
        var jsonAttr = clickEl.getAttribute('data-click-json');
        if (jsonAttr) {
          // data-click-json: pass parsed JSON object as single argument
          try { fn(JSON.parse(jsonAttr)); } catch(e) {}
        } else {
          var args = parseArgs(clickEl.getAttribute('data-click-args'));
          if (clickEl.hasAttribute('data-click-pass-el')) {
            args.push(clickEl);
          }
          fn.apply(null, args);
        }
      }
      // data-click-also (second function call after primary)
      var also = clickEl.getAttribute('data-click-also');
      if (also) {
        var alsoFn = resolve(also);
        if (alsoFn) {
          var alsoArgs = parseArgs(clickEl.getAttribute('data-click-also-args'));
          alsoFn.apply(null, alsoArgs);
        }
      }
      // data-click-hide + data-click-also-show (swap visibility)
      if (clickEl.hasAttribute('data-click-hide')) {
        var hideTarget = document.getElementById(clickEl.getAttribute('data-click-hide'));
        if (hideTarget) hideTarget.classList.add('hidden');
      }
      if (clickEl.hasAttribute('data-click-also-show')) {
        var showTarget = document.getElementById(clickEl.getAttribute('data-click-also-show'));
        if (showTarget) showTarget.classList.remove('hidden');
      }
    }
  }, false);

  // ── CHANGE delegation ─────────────────────────────────────────────
  document.addEventListener('change', function(e) {
    // data-change-search (select → navigate)
    var navEl = e.target.closest('[data-change-search]');
    if (navEl) {
      var tpl = navEl.getAttribute('data-change-search');
      window.location.search = tpl.replace('{value}', navEl.value);
      return;
    }

    var el = e.target.closest('[data-change]');
    if (!el) return;
    var fn = resolve(el.getAttribute('data-change'));
    if (!fn) return;
    var args = parseArgs(el.getAttribute('data-change-args'));
    args = appendPass(el, el.getAttribute('data-change-pass'), args);
    fn.apply(null, args);
  }, false);

  // ── INPUT delegation ──────────────────────────────────────────────
  document.addEventListener('input', function(e) {
    var el = e.target.closest('[data-input]');
    if (!el) return;
    var fn = resolve(el.getAttribute('data-input'));
    if (!fn) return;
    var args = parseArgs(el.getAttribute('data-input-args'));
    args = appendPass(el, el.getAttribute('data-input-pass'), args);
    fn.apply(null, args);
  }, false);

  // ── KEYUP delegation ──────────────────────────────────────────────
  document.addEventListener('keyup', function(e) {
    var el = e.target.closest('[data-keyup]');
    if (!el) return;
    var fn = resolve(el.getAttribute('data-keyup'));
    if (!fn) return;
    var args = parseArgs(el.getAttribute('data-keyup-args'));
    fn.apply(null, args);
  }, false);

  // ── SUBMIT delegation ─────────────────────────────────────────────
  document.addEventListener('submit', function(e) {
    var form = e.target.closest('[data-submit-action]');
    if (form) {
      e.preventDefault();
      var fn = resolve(form.getAttribute('data-submit-action'));
      if (fn) fn(e);
      return;
    }
    // data-submit-confirm (window.confirm before submit)
    var confirmForm = e.target.closest('[data-submit-confirm]');
    if (confirmForm) {
      var msg = confirmForm.getAttribute('data-submit-confirm');
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    }
  }, false);

  // ── IMAGE FALLBACK (error does not bubble — use capture) ──────────
  document.addEventListener('error', function(e) {
    if (e.target.tagName !== 'IMG') return;
    var img = e.target;
    if (img.hasAttribute('data-fallback-src')) {
      var fallback = img.getAttribute('data-fallback-src');
      if (img.src !== fallback && !img._cspFallbackApplied) {
        img._cspFallbackApplied = true;
        img.src = fallback;
      }
    } else if (img.getAttribute('data-fallback') === 'hide') {
      img.style.display = 'none';
    } else if (img.getAttribute('data-fallback') === 'hide-show-next') {
      img.style.display = 'none';
      var next = img.nextElementSibling;
      if (next) {
        next.style.display = next.style.display === 'none' ? 'flex' : '';
        next.classList.remove('hidden');
        next.classList.add('flex');
      }
    } else if (img.hasAttribute('data-fallback-text')) {
      var text = img.getAttribute('data-fallback-text');
      var span = document.createElement('span');
      span.textContent = text;
      span.className = img.hasAttribute('data-fallback-class')
        ? img.getAttribute('data-fallback-class')
        : img.className;
      img.replaceWith(span);
    }
  }, true);

  // ── GLOBAL HELPERS (used via data-click) ──────────────────────────
  /**
   * Remove the closest <tr> ancestor of the clicked element,
   * then call the named sync function with the textarea ID.
   * Usage: data-click="__removeRowAndSync" data-click-args='["syncFunc","textareaId"]' data-click-pass-el
   */
  window.__removeRowAndSync = function(syncFuncName, textareaId, el) {
    if (el) {
      var tr = el.closest('tr');
      if (tr) tr.remove();
    }
    var fn = window[syncFuncName];
    if (typeof fn === 'function') fn(textareaId);
  };

  /**
   * Remove an element by ID.
   * Usage: data-click="__removeById" data-click-args='["elementId"]'
   */
  window.__removeById = function(elementId) {
    var el = document.getElementById(elementId);
    if (el) el.remove();
  };

  /**
   * Copy the value of an element matching a CSS selector to clipboard.
   * Usage: data-click="__copySelector" data-click-args='["#selector"]'
   */
  window.__copySelector = function(selector) {
    var el = document.querySelector(selector);
    if (el && navigator.clipboard) {
      navigator.clipboard.writeText(el.value || el.textContent).then(function() {
        if (window.TOC && TOC.toast) TOC.toast('Copied!', 'success');
        else if (window.showToast) window.showToast({type: 'success', message: 'Copied to clipboard!'});
      });
    }
  };

  /**
   * Dispatch a named event on the closest ancestor matching a selector.
   * Usage: data-click="__dispatchOnClosest" data-click-args='[".modal-overlay","close"]' data-click-pass-el
   */
  window.__dispatchOnClosest = function(selector, eventName, el) {
    if (el) {
      var target = el.closest(selector);
      if (target) target.dispatchEvent(new Event(eventName));
    }
  };

})();
