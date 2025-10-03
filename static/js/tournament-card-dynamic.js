/**
 * Dynamic Tournament Card Registration Buttons
 * Loads registration button states via AJAX for each tournament card
 */

(function() {
  'use strict';

  // Initialize all tournament cards on page load
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[Tournament Card Dynamic] Initializing...');
    const containers = document.querySelectorAll('.dc-reg-btn-container[data-loading="true"]');
    console.log('[Tournament Card Dynamic] Found', containers.length, 'containers');
    
    containers.forEach((container, index) => {
      const slug = container.dataset.tournamentSlug;
      console.log(`[Tournament Card Dynamic] Container ${index + 1}:`, {
        slug: slug,
        element: container,
        dataset: container.dataset
      });
      
      if (slug && slug !== 'undefined' && slug !== '') {
        loadRegistrationButton(container, slug);
      } else {
        console.warn('Tournament slug is missing or invalid:', slug, container);
        renderFallbackButton(container, 'Invalid tournament');
      }
    });
  });

  /**
   * Fetch registration context and render appropriate button
   */
  function loadRegistrationButton(container, slug) {
    fetch(`/tournaments/api/${slug}/register/context/`)
      .then(response => response.json())
      .then(data => {
        if (data.success && data.context) {
          renderButton(container, data.context, slug);
        } else {
          renderFallbackButton(container, data.error || 'Unavailable');
        }
      })
      .catch(error => {
        console.error(`Failed to load registration button for ${slug}:`, error);
        renderFallbackButton(container, 'Error loading');
      });
  }

  /**
   * Render the appropriate button based on context
   */
  function renderButton(container, context, slug) {
    let html = '';
    const state = context.button_state;
    const text = context.button_text || 'Register';
    const message = context.message || '';

    switch (state) {
      case 'register':
        // Open for registration
        html = `
          <a class="dc-btn" href="/tournaments/register-modern/${slug}/" aria-label="${text}">
            <i class="fa-solid fa-user-plus"></i> ${text}
          </a>
        `;
        break;

      case 'registered':
        // Already registered
        html = `
          <button class="dc-btn dc-btn-registered" disabled aria-disabled="true">
            <i class="fa-solid fa-check-circle"></i> ${text}
          </button>
        `;
        break;

      case 'request_approval':
        // Team member needs captain approval
        html = `
          <a class="dc-btn dc-btn-approval" href="/tournaments/register-modern/${slug}/" aria-label="${text}">
            <i class="fa-solid fa-paper-plane"></i> ${text}
          </a>
        `;
        break;

      case 'request_pending':
        // Approval request pending
        html = `
          <button class="dc-btn dc-btn-pending" disabled aria-disabled="true">
            <i class="fa-solid fa-hourglass-half"></i> ${text}
          </button>
        `;
        break;

      case 'closed':
        // Registration closed
        html = `
          <button class="dc-btn dc-btn-disabled" disabled aria-disabled="true">
            <i class="fa-solid fa-lock"></i> ${text}
          </button>
        `;
        break;

      case 'started':
        // Tournament already started
        html = `
          <button class="dc-btn dc-btn-disabled" disabled aria-disabled="true">
            <i class="fa-solid fa-flag"></i> ${text}
          </button>
        `;
        break;

      case 'full':
        // Tournament is full
        html = `
          <button class="dc-btn dc-btn-disabled" disabled aria-disabled="true">
            <i class="fa-solid fa-users"></i> ${text}
          </button>
        `;
        break;

      case 'no_team':
        // Team member without team
        html = `
          <button class="dc-btn dc-btn-warning" disabled aria-disabled="true">
            <i class="fa-solid fa-exclamation-triangle"></i> ${text}
          </button>
        `;
        break;

      default:
        // Unknown state - show generic disabled button
        html = `
          <button class="dc-btn dc-btn-disabled" disabled aria-disabled="true">
            <i class="fa-solid fa-ban"></i> Unavailable
          </button>
        `;
    }

    container.innerHTML = html;
    container.dataset.loading = 'false';
    
    // Add tooltip if message exists
    if (message && container.querySelector('.dc-btn')) {
      const btn = container.querySelector('.dc-btn');
      btn.setAttribute('title', message);
      btn.setAttribute('data-tooltip', message);
    }
  }

  /**
   * Render fallback button when API call fails
   */
  function renderFallbackButton(container, errorMsg) {
    container.innerHTML = `
      <button class="dc-btn dc-btn-disabled" disabled aria-disabled="true">
        <i class="fa-solid fa-exclamation-circle"></i> ${errorMsg}
      </button>
    `;
    container.dataset.loading = 'false';
  }

  // Export for use in other scripts if needed
  window.TournamentCardDynamic = {
    loadRegistrationButton,
    renderButton,
    renderFallbackButton
  };

})();
