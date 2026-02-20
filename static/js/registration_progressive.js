/**
 * Progressive Disclosure JS — Registration Form
 * DeltaCrown Smart Registration UX Upgrade
 * Task: P1-T03
 *
 * Features:
 * - Auto-collapse fully-filled sections
 * - Auto-expand sections needing input
 * - Click-to-toggle section collapse
 * - Scroll-to-first-error on submit failure
 * - Mobile mini-nav dot navigation
 * - Section readiness tracking
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    // ── Section Discovery ──
    var sections = document.querySelectorAll('.reg-section[data-section]');
    if (!sections.length) return;

    // ── Collapsible Toggle ──
    sections.forEach(function (section) {
      var chevron = section.querySelector('.chevron-toggle');
      var header = chevron ? chevron.parentElement : null;
      if (!header) return;

      header.addEventListener('click', function (e) {
        // Don't toggle if clicking a link or button inside header
        if (e.target.closest('a, button, input')) return;
        toggleSection(section);
      });

      // Keyboard accessibility
      header.setAttribute('tabindex', '0');
      header.setAttribute('role', 'button');
      header.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleSection(section);
        }
      });
    });

    function toggleSection(section) {
      section.classList.toggle('collapsed');
      var expanded = !section.classList.contains('collapsed');
      var chevronEl = section.querySelector('.chevron-toggle');
      var headerEl = chevronEl ? chevronEl.parentElement : null;
      if (headerEl) headerEl.setAttribute('aria-expanded', expanded);
      updateMiniNav();
    }

    // ── Auto-Collapse Logic ──
    // Sections flagged with data-complete="true" start collapsed
    sections.forEach(function (section) {
      var isComplete = section.dataset.complete === 'true';
      var isCollapsible = section.dataset.collapsible !== 'false';
      if (isComplete && isCollapsible) {
        section.classList.add('collapsed');
      }
    });

    // ── Summary Bar Update ──
    function updateSummaryBar() {
      var summaryItems = document.querySelectorAll('.summary-bar [data-summary-section]');
      sections.forEach(function (section) {
        var name = section.dataset.section;
        var statusEl = section.querySelector('.section-status');
        var isComplete = checkSectionComplete(section);

        // Update section status badge
        if (statusEl) {
          if (isComplete) {
            statusEl.className = 'section-status complete';
            statusEl.innerHTML = '<i data-lucide="check" class="w-2.5 h-2.5 inline -mt-px"></i> Complete';
          } else {
            statusEl.className = 'section-status attention';
            statusEl.innerHTML = '<i data-lucide="alert-circle" class="w-2.5 h-2.5 inline -mt-px"></i> Needs Input';
          }
        }
      });

      // Update progress segments
      var segments = document.querySelectorAll('[data-segment]');
      segments.forEach(function (seg) {
        var sectionName = seg.dataset.segment;
        var section = document.querySelector('.reg-section[data-section="' + sectionName + '"]');
        if (section) {
          var isComplete = checkSectionComplete(section);
          seg.classList.remove('bg-emerald-500', 'bg-yellow-500');
          seg.classList.add(isComplete ? 'bg-emerald-500' : 'bg-yellow-500');
        }
      });

      // Refresh lucide icons if available
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function checkSectionComplete(section) {
      // A section is complete if all required inputs have values
      var requiredInputs = section.querySelectorAll('input[required], select[required], textarea[required]');
      var allFilled = true;
      requiredInputs.forEach(function (input) {
        if (!input.value || !input.value.trim()) allFilled = false;
      });

      // Also check if section is marked complete from server
      if (section.dataset.complete === 'true') return true;

      // If no required inputs, consider it complete
      if (!requiredInputs.length) return true;

      return allFilled;
    }

    // Listen for input changes to update summary
    document.querySelectorAll('.reg-section input, .reg-section select, .reg-section textarea').forEach(function (el) {
      el.addEventListener('input', debounce(updateSummaryBar, 300));
      el.addEventListener('change', updateSummaryBar);
    });

    // Initial summary update
    updateSummaryBar();

    // ── Scroll-to-Error on Submit ──
    var form = document.getElementById('smart-reg-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        // Find first invalid field
        var firstInvalid = form.querySelector(':invalid');
        if (firstInvalid) {
          e.preventDefault();

          // Expand parent section if collapsed
          var parentSection = firstInvalid.closest('.reg-section');
          if (parentSection && parentSection.classList.contains('collapsed')) {
            parentSection.classList.remove('collapsed');
          }

          // Add error styling
          var fieldWrapper = firstInvalid.closest('div');
          if (fieldWrapper) {
            fieldWrapper.classList.add('field-error');
            setTimeout(function () { fieldWrapper.classList.remove('field-error'); }, 5000);
          }

          // Scroll into view
          firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });

          // Focus after scroll animation
          setTimeout(function () { firstInvalid.focus(); }, 400);
        }
      });
    }

    // ── Mini-Nav Dots ──
    var miniNav = document.querySelector('.mini-nav');
    if (miniNav) {
      var dots = miniNav.querySelectorAll('.mini-nav-dot');

      // Click to scroll
      dots.forEach(function (dot) {
        dot.addEventListener('click', function () {
          var target = dot.dataset.target;
          var section = document.querySelector('.reg-section[data-section="' + target + '"]');
          if (section) {
            // Expand if collapsed
            if (section.classList.contains('collapsed')) {
              section.classList.remove('collapsed');
            }
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });
      });

      // Update active dot on scroll
      var scrollHandler = debounce(function () {
        var activeSection = null;
        var viewportMiddle = window.innerHeight / 3;

        sections.forEach(function (section) {
          var rect = section.getBoundingClientRect();
          if (rect.top < viewportMiddle && rect.bottom > 0) {
            activeSection = section.dataset.section;
          }
        });

        dots.forEach(function (dot) {
          dot.classList.toggle('active', dot.dataset.target === activeSection);
        });
      }, 100);

      window.addEventListener('scroll', scrollHandler, { passive: true });
    }

    function updateMiniNav() {
      if (!miniNav) return;
      var dots = miniNav.querySelectorAll('.mini-nav-dot');
      dots.forEach(function (dot) {
        var target = dot.dataset.target;
        var section = document.querySelector('.reg-section[data-section="' + target + '"]');
        if (section) {
          var isComplete = checkSectionComplete(section);
          dot.classList.toggle('complete', isComplete);
          dot.classList.toggle('attention', !isComplete);
        }
      });
    }

    updateMiniNav();

    // ── Locked Field Tooltips ──
    document.querySelectorAll('.badge-auto[data-source]').forEach(function (badge) {
      var source = badge.dataset.source;
      var tooltipText = {
        'profile': 'Auto-filled from your DeltaCrown profile',
        'username': 'Your DeltaCrown username (cannot be changed here)',
        'account': 'Verified account email (cannot be changed here)',
        'game_passport': 'Verified from your Game Passport',
        'default': 'Default value',
      };
      badge.classList.add('locked-tooltip');
      badge.setAttribute('data-tooltip', tooltipText[source] || 'Auto-filled');
    });

    // ── Utility ──
    function debounce(fn, delay) {
      var timer;
      return function () {
        var args = arguments;
        var ctx = this;
        clearTimeout(timer);
        timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
      };
    }
  });
})();
