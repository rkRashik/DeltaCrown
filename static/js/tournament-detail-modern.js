/**
 * Dynamic Registration Buttons for Tournament Detail Page
 * Handles multiple registration button locations (hero, sidebar, mobile)
 */

(function() {
  'use strict';

  // Initialize all registration buttons on page load
  document.addEventListener('DOMContentLoaded', function() {
    const heroBtn = document.getElementById('hero-registration-btn');
    const sidebarBtn = document.getElementById('sidebar-registration-btn');
    const mobileBtn = document.getElementById('mobile-registration-btn');

    if (heroBtn) {
      const slug = heroBtn.dataset.tournamentSlug;
      if (slug) {
        loadRegistrationButtons(slug, [
          { element: heroBtn, variant: 'large' },
          { element: sidebarBtn, variant: 'compact' },
          { element: mobileBtn, variant: 'large' }
        ]);
      }
    }
  });

  /**
   * Fetch registration context once and update all button locations
   */
  function loadRegistrationButtons(slug, locations) {
    dcLog('[Tournament Detail] Loading buttons for slug:', slug);
    fetch(`/tournaments/api/${slug}/register/context/`)
      .then(response => response.json())
      .then(data => {
        dcLog('[Tournament Detail] API Response:', data);
        if (data.success && data.context) {
          locations.forEach(loc => {
            if (loc.element) {
              renderDetailButton(loc.element, data.context, slug, loc.variant);
            }
          });
        } else {
          locations.forEach(loc => {
            if (loc.element) {
              renderErrorButton(loc.element, data.error || 'Unavailable', loc.variant);
            }
          });
        }
      })
      .catch(error => {
        console.error('[Tournament Detail] Failed to load registration context:', error);
        locations.forEach(loc => {
          if (loc.element) {
            renderErrorButton(loc.element, 'Error loading', loc.variant);
          }
        });
      });
  }

  /**
   * Render button based on state and variant (large/compact)
   */
  function renderDetailButton(container, context, slug, variant) {
    const state = context.button_state;
    const text = context.button_text || 'Register';
    const message = context.message || '';
    const isLarge = variant === 'large';
    const sizeClass = isLarge ? 'big wfull' : '';
    
    dcLog('[Tournament Detail] Rendering button:', { slug, state, text });
    
    let html = '';
    let helpText = message ? `<p class="small muted" style="margin-top:.35rem;">${escapeHtml(message)}</p>` : '';

    switch (state) {
      case 'not_authenticated':
        html = `
          <a class="btn-neo ${sizeClass}" href="/accounts/login/?next=/tournaments/register-modern/${slug}/">
            <i class="fa-solid fa-right-to-bracket"></i> ${escapeHtml(text)}
          </a>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'register':
        html = `
          <a class="btn-neo ${sizeClass}" href="/tournaments/register-modern/${slug}/">
            <i class="fa-solid fa-user-plus"></i> ${escapeHtml(text)}
          </a>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'registered':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true" style="background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); color: #10b981;">
            <i class="fa-solid fa-check-circle"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'request_approval':
        html = `
          <a class="btn-neo ${sizeClass}" href="/tournaments/register-modern/${slug}/" style="background: rgba(251, 146, 60, 0.1); border-color: rgba(251, 146, 60, 0.3); color: #fb923c;">
            <i class="fa-solid fa-paper-plane"></i> ${escapeHtml(text)}
          </a>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'request_pending':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true" style="background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.3); color: #fbbf24;">
            <i class="fa-solid fa-hourglass-half"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'closed':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true">
            <i class="fa-solid fa-lock"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'started':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true">
            <i class="fa-solid fa-flag"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'full':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true">
            <i class="fa-solid fa-users"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      case 'no_team':
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true" style="background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #ef4444;">
            <i class="fa-solid fa-exclamation-triangle"></i> ${escapeHtml(text)}
          </button>
          ${isLarge ? helpText : ''}
        `;
        break;

      default:
        html = `
          <button class="btn-neo ${sizeClass}" disabled aria-disabled="true">
            <i class="fa-solid fa-ban"></i> Unavailable
          </button>
        `;
    }

    container.innerHTML = html;
  }

  /**
   * Render error/fallback button
   */
  function renderErrorButton(container, errorMsg, variant) {
    const isLarge = variant === 'large';
    const sizeClass = isLarge ? 'big wfull' : '';
    
    container.innerHTML = `
      <button class="btn-neo ${sizeClass}" disabled aria-disabled="true">
        <i class="fa-solid fa-exclamation-circle"></i> ${escapeHtml(errorMsg)}
      </button>
    `;
  }

  /**
   * Simple HTML escape helper
   */
  function escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  // Export for debugging
  window.TournamentDetailModern = {
    loadRegistrationButtons,
    renderDetailButton,
    renderErrorButton
  };

})();
