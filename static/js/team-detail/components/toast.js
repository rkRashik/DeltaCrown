/**
 * Toast Notification Component
 */

class Toast {
  /**
   * Show a toast notification
   * @param {string} message - The message to display
   * @param {string} type - Type: success, error, warning, info
   * @param {number} duration - Duration in ms (0 for persistent)
   */
  static show(message, type = 'info', duration = 3000) {
    let container = document.getElementById('toast-container');
    
    // Create container if it doesn't exist
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <i class="toast-icon fa-solid fa-${this.getIcon(type)}"></i>
        <span class="toast-message">${this.escapeHtml(message)}</span>
      </div>
      <button class="toast-close">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Close button handler
    const closeButton = toast.querySelector('.toast-close');
    closeButton.addEventListener('click', () => this.hide(toast));

    // Auto-hide
    if (duration > 0) {
      setTimeout(() => this.hide(toast), duration);
    }

    return toast;
  }

  /**
   * Hide and remove a toast
   */
  static hide(toast) {
    toast.classList.remove('show');
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  /**
   * Get icon for toast type
   */
  static getIcon(type) {
    const icons = {
      success: 'circle-check',
      error: 'circle-xmark',
      warning: 'triangle-exclamation',
      info: 'circle-info'
    };
    return icons[type] || icons.info;
  }

  /**
   * Escape HTML to prevent XSS
   */
  static escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Convenience methods
   */
  static success(message, duration = 3000) {
    return this.show(message, 'success', duration);
  }

  static error(message, duration = 4000) {
    return this.show(message, 'error', duration);
  }

  static warning(message, duration = 3500) {
    return this.show(message, 'warning', duration);
  }

  static info(message, duration = 3000) {
    return this.show(message, 'info', duration);
  }
}

// Make Toast available globally
window.Toast = Toast;

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Toast;
}
