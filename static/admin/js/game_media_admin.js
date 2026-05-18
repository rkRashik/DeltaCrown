/**
 * DeltaCrown Game Media Admin — Safe Preview Enhancement
 *
 * RULE: Never hide, clone, move, or replace Django's file input rows.
 * Only inserts a read-only thumbnail strip ABOVE the existing fields,
 * and wires the original inputs for live-preview on change.
 *
 * Form submission is 100% unaffected.
 */
(function () {
  'use strict';

  var FIELDS = [
    { name: 'icon',       label: 'Icon',        hint: '~256×256 px, square PNG' },
    { name: 'logo',       label: 'Logo',         hint: '~400×150 px, with transparency' },
    { name: 'banner',     label: 'Banner',       hint: '~1280×400 px, landscape' },
    { name: 'card_image', label: 'Card Image',   hint: '~600×400 px, card thumbnail' },
  ];

  /* ── Build a read-only preview card ──────────────────────────────── */
  function buildThumb(field, url) {
    var card = document.createElement('div');
    card.className = 'gma-thumb-card';
    card.setAttribute('data-gma-field', field.name);

    var thumb = document.createElement('div');
    thumb.className = 'gma-thumb-img-area';

    if (url) {
      var img = document.createElement('img');
      img.src = url;
      img.alt = field.label;
      img.className = 'gma-thumb-img';
      img.onerror = function () {
        this.style.display = 'none';
        var ph = thumb.querySelector('.gma-thumb-ph');
        if (ph) ph.style.display = 'flex';
      };
      thumb.appendChild(img);
    }

    var ph = document.createElement('div');
    ph.className = 'gma-thumb-ph';
    ph.style.display = url ? 'none' : 'flex';
    ph.innerHTML = '<span class="material-symbols-outlined" style="font-size:20px;">image_not_supported</span>';
    thumb.appendChild(ph);

    card.appendChild(thumb);

    var info = document.createElement('div');
    info.className = 'gma-thumb-info';

    var lbl = document.createElement('span');
    lbl.className = 'gma-thumb-lbl';
    lbl.textContent = field.label.toUpperCase();
    info.appendChild(lbl);

    if (url) {
      var a = document.createElement('a');
      a.href = url;
      a.target = '_blank';
      a.rel = 'noopener';
      a.className = 'gma-thumb-open';
      a.textContent = 'Open';
      info.appendChild(a);
    }

    card.appendChild(info);

    var hint = document.createElement('div');
    hint.className = 'gma-thumb-hint';
    hint.textContent = field.hint;
    card.appendChild(hint);

    return card;
  }

  /* ── Get current file URL from Django's "Currently: <a>" link ───── */
  function getCurrentUrl(fieldRow) {
    var a = fieldRow && fieldRow.querySelector('a[href]');
    return a ? a.href : '';
  }

  /* ── Wire original input → update thumbnail on file select ───────── */
  function wirePreview(fieldName, card) {
    var input = document.getElementById('id_' + fieldName);
    if (!input) return;

    input.addEventListener('change', function () {
      var file = this.files && this.files[0];
      if (!file || !file.type.startsWith('image/')) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        var thumbArea = card.querySelector('.gma-thumb-img-area');
        var img = card.querySelector('.gma-thumb-img');
        var ph  = card.querySelector('.gma-thumb-ph');
        if (!img) {
          img = document.createElement('img');
          img.className = 'gma-thumb-img';
          img.alt = fieldName;
          if (thumbArea) thumbArea.insertBefore(img, thumbArea.firstChild);
        }
        img.src = e.target.result;
        img.style.display = 'block';
        if (ph) ph.style.display = 'none';
      };
      reader.readAsDataURL(file);
    });
  }

  /* ── Main: insert thumbnail strip before first media field row ───── */
  function run() {
    // Only run on Game change pages — check at least one media field exists
    var firstFieldRow = null;
    FIELDS.forEach(function (f) {
      if (!firstFieldRow) {
        firstFieldRow = document.querySelector('.field-' + f.name);
      }
    });
    if (!firstFieldRow) return;

    var strip = document.createElement('div');
    strip.className = 'gma-strip';

    var hasAny = false;
    FIELDS.forEach(function (f) {
      var row = document.querySelector('.field-' + f.name);
      if (!row) return;
      var url = getCurrentUrl(row);
      var card = buildThumb(f, url);
      strip.appendChild(card);
      wirePreview(f.name, card);
      hasAny = true;
    });

    if (!hasAny) return;

    // Insert BEFORE the first media field row — original rows unchanged
    firstFieldRow.parentNode.insertBefore(strip, firstFieldRow);
  }

  /* ── MapPool inline: live preview on image input change ──────────── */
  function wireMapPoolPreviews() {
    function wire(input) {
      if (input._gpWired) return;
      input._gpWired = true;
      input.addEventListener('change', function () {
        var file = this.files && this.files[0];
        if (!file || !file.type.startsWith('image/')) return;
        var reader = new FileReader();
        var cell = input.closest('td') || input.closest('.field-image') || input.parentNode;
        reader.onload = function (e) {
          var img = cell.querySelector('.gma-map-inline-prev');
          if (!img) {
            img = document.createElement('img');
            img.className = 'gma-map-inline-prev';
            img.style.cssText = 'display:block;height:34px;width:auto;border-radius:4px;margin-top:5px;border:1px solid #e5e7eb;object-fit:contain;';
            input.insertAdjacentElement('afterend', img);
          }
          img.src = e.target.result;
        };
        reader.readAsDataURL(file);
      });
    }

    document.querySelectorAll('#gamemappool_set-group input[type="file"]').forEach(wire);

    // Watch for new inline rows added dynamically
    var inlineGroup = document.getElementById('gamemappool_set-group');
    if (inlineGroup && window.MutationObserver) {
      var obs = new MutationObserver(function () {
        inlineGroup.querySelectorAll('input[type="file"]:not([data-wired])').forEach(function (inp) {
          inp.setAttribute('data-wired', '1');
          wire(inp);
        });
      });
      obs.observe(inlineGroup, { childList: true, subtree: true });
    }
  }

  function init() {
    run();
    wireMapPoolPreviews();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
