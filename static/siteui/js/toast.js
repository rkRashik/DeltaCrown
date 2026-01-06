/**
 * Phase 9A-24: Modern Toast Notification System
 * Using Toastify.js with Tailwind-styled glass morphism design
 * 
 * Usage:
 *   showToast({type: 'success', message: 'Saved!'})
 *   showToast({type: 'error', title: 'Error', message: 'Something went wrong'})
 *   showToast({type: 'info', message: 'Just FYI'})
 *   showToast({type: 'warning', message: 'Be careful!'})
 */

(function() {
  'use strict';

  // Check if Toastify is loaded
  if (typeof Toastify === 'undefined') {
    console.warn('[Toast] Toastify.js not loaded. Falling back to console.');
    window.showToast = function(opts) {
      const msg = (opts.title ? opts.title + ': ' : '') + opts.message;
      console.log('[Toast]', opts.type || 'info', msg);
    };
    return;
  }

  /**
   * Show a modern toast notification
   * @param {Object} options - Toast configuration
   * @param {string} options.type - Toast type: 'success', 'error', 'warning', 'info'
   * @param {string} [options.title] - Optional toast title
   * @param {string} options.message - Toast message (required)
   * @param {number} [options.duration] - Duration in milliseconds (default: 5000)
   * @param {boolean} [options.close] - Show close button (default: true)
   */
  window.showToast = function(options) {
    if (!options || !options.message) {
      console.error('[Toast] Message is required');
      return;
    }

    const {
      type = 'info',
      title,
      message,
      duration = 5000,
      close = true
    } = options;

    // Icon mapping
    const iconMap = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };

    // Background gradient mapping (glass morphism)
    const bgMap = {
      success: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.15) 100%)',
      error: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%)',
      warning: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.15) 100%)',
      info: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%)'
    };

    // Border color mapping
    const borderMap = {
      success: 'rgba(16, 185, 129, 0.3)',
      error: 'rgba(239, 68, 68, 0.3)',
      warning: 'rgba(245, 158, 11, 0.3)',
      info: 'rgba(59, 130, 246, 0.3)'
    };

    // Text color mapping
    const textMap = {
      success: '#10b981',
      error: '#ef4444',
      warning: '#f59e0b',
      info: '#3b82f6'
    };

    // Build toast HTML
    let html = `
      <div style="display: flex; align-items: flex-start; gap: 12px; min-width: 280px; max-width: 400px;">
        <div style="
          flex-shrink: 0;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: ${bgMap[type]};
          border: 1.5px solid ${borderMap[type]};
          display: flex;
          align-items: center;
          justify-content: center;
          color: ${textMap[type]};
          font-weight: bold;
          font-size: 18px;
        ">
          ${iconMap[type]}
        </div>
        <div style="flex: 1; min-width: 0;">
    `;

    if (title) {
      html += `
        <div style="
          font-weight: 700;
          font-size: 14px;
          color: #ffffff;
          margin-bottom: 4px;
          line-height: 1.3;
        ">
          ${escapeHtml(title)}
        </div>
      `;
    }

    html += `
        <div style="
          font-size: 13px;
          color: rgba(255, 255, 255, 0.85);
          line-height: 1.5;
          word-wrap: break-word;
        ">
          ${escapeHtml(message)}
        </div>
      </div>
    `;

    if (close) {
      html += `
        <button class="toast-close-btn" style="
          flex-shrink: 0;
          width: 24px;
          height: 24px;
          border-radius: 6px;
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
          font-weight: bold;
          transition: all 0.2s;
          margin-left: auto;
        " onmouseover="this.style.background='rgba(255,255,255,0.2)'; this.style.color='#fff';" onmouseout="this.style.background='rgba(255,255,255,0.1)'; this.style.color='rgba(255,255,255,0.6)';">
          ✕
        </button>
      `;
    }

    html += `</div>`;

    // Detect mobile
    const isMobile = window.innerWidth < 768;

    // Show toast
    const toast = Toastify({
      text: html,
      duration: duration,
      close: false, // We handle close button manually
      gravity: isMobile ? 'top' : 'bottom',
      position: isMobile ? 'center' : 'right',
      stopOnFocus: true,
      escapeMarkup: false,
      style: {
        background: bgMap[type],
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: `1px solid ${borderMap[type]}`,
        borderRadius: '16px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
        padding: '16px 18px',
        minWidth: '280px',
        maxWidth: '420px',
        marginTop: isMobile ? '16px' : '0',
        marginBottom: isMobile ? '0' : '16px'
      },
      offset: {
        x: isMobile ? 0 : 24,
        y: isMobile ? 0 : 24
      },
      onClick: function() {
        // Only close if clicking toast body, not close button
        // Close button will trigger its own handler
      }
    }).showToast();
    
    // Phase 9A-27: Add close button click handler after toast is shown
    setTimeout(() => {
      const toastEl = document.querySelector('.toastify:last-of-type');
      if (toastEl) {
        const closeBtn = toastEl.querySelector('.toast-close-btn');
        if (closeBtn) {
          closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toast.hideToast();
          });
        }
      }
    }, 50);
  };

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  console.log('[Toast] Modern toast system initialized (Phase 9A-24)');
})();
