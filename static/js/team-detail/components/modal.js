/**
 * Modal Component
 */

class Modal {
  constructor(options = {}) {
    this.title = options.title || '';
    this.content = options.content || '';
    this.footer = options.footer || '';
    this.size = options.size || 'medium'; // small, medium, large
    this.onClose = options.onClose || null;
    this.overlay = null;
  }

  /**
   * Open the modal
   */
  open() {
    // Create modal if it doesn't exist
    this.overlay = document.getElementById('modal-overlay');
    
    if (!this.overlay) {
      this.overlay = document.createElement('div');
      this.overlay.id = 'modal-overlay';
      this.overlay.className = 'modal-overlay';
      document.body.appendChild(this.overlay);
    }

    // Build modal HTML
    this.overlay.innerHTML = `
      <div class="modal-container modal-${this.size}">
        <div class="modal-header">
          <h2 class="modal-title">${this.escapeHtml(this.title)}</h2>
          <button class="modal-close" id="modal-close-btn">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="modal-body" id="modal-body">
          ${this.content}
        </div>
        ${this.footer ? `<div class="modal-footer">${this.footer}</div>` : ''}
      </div>
    `;

    // Show modal
    this.overlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Add event listeners
    this.addEventListeners();
  }

  /**
   * Close the modal
   */
  close() {
    if (this.overlay) {
      this.overlay.classList.remove('active');
      document.body.style.overflow = '';

      // Remove overlay after animation
      setTimeout(() => {
        if (this.overlay && this.overlay.parentNode) {
          this.overlay.parentNode.removeChild(this.overlay);
        }
      }, 300);
    }

    // Call onClose callback
    if (this.onClose) {
      this.onClose();
    }
  }

  /**
   * Update modal content
   */
  updateContent(content) {
    const body = document.getElementById('modal-body');
    if (body) {
      body.innerHTML = content;
    }
  }

  /**
   * Add event listeners
   */
  addEventListeners() {
    // Close button
    const closeBtn = document.getElementById('modal-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.close());
    }

    // Click outside to close
    if (this.overlay) {
      this.overlay.addEventListener('click', (e) => {
        if (e.target === this.overlay) {
          this.close();
        }
      });
    }

    // ESC key to close
    const escHandler = (e) => {
      if (e.key === 'Escape') {
        this.close();
        document.removeEventListener('keydown', escHandler);
      }
    };
    document.addEventListener('keydown', escHandler);
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Static method to create and open modal
   */
  static create(options) {
    const modal = new Modal(options);
    modal.open();
    return modal;
  }

  /**
   * Confirmation dialog
   */
  static confirm(title, message, onConfirm) {
    return Modal.create({
      title: title,
      content: `<p>${message}</p>`,
      footer: `
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').dispatchEvent(new Event('close'))">
          Cancel
        </button>
        <button class="btn btn-primary" onclick="this.closest('.modal-overlay').dispatchEvent(new Event('confirm'))">
          Confirm
        </button>
      `,
      size: 'small',
      onClose: function() {
        // Handle confirmation
        this.overlay.addEventListener('confirm', () => {
          if (onConfirm) onConfirm();
          this.close();
        });
        this.overlay.addEventListener('close', () => {
          this.close();
        });
      }
    });
  }
}

// Make Modal available globally
window.Modal = Modal;

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Modal;
}
