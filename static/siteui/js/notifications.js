/**
 * Modern Professional Toast Notification System
 * Displays success, error, warning, and info messages with animations
 */

(function() {
  'use strict';

  // Initialize DC namespace
  window.DC = window.DC || {};

  // Toast types with icons and colors
  const TOAST_TYPES = {
    success: {
      icon: 'fa-circle-check',
      color: '#10b981',
      bgColor: '#d1fae5',
      borderColor: '#6ee7b7'
    },
    error: {
      icon: 'fa-circle-xmark',
      color: '#ef4444',
      bgColor: '#fee2e2',
      borderColor: '#fca5a5'
    },
    warning: {
      icon: 'fa-triangle-exclamation',
      color: '#f59e0b',
      bgColor: '#fef3c7',
      borderColor: '#fcd34d'
    },
    info: {
      icon: 'fa-circle-info',
      color: '#3b82f6',
      bgColor: '#dbeafe',
      borderColor: '#93c5fd'
    }
  };

  // Toast container
  let toastContainer = null;

  // Initialize container
  function initContainer() {
    if (toastContainer) return toastContainer;

    toastContainer = document.createElement('div');
    toastContainer.id = 'modern-toast-container';
    toastContainer.setAttribute('aria-live', 'polite');
    toastContainer.setAttribute('aria-atomic', 'true');
    
    // Styling
    Object.assign(toastContainer.style, {
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      maxWidth: '420px',
      pointerEvents: 'none'
    });

    document.body.appendChild(toastContainer);
    return toastContainer;
  }

  /**
   * Show a toast notification
   * @param {Object} options - Toast options
   * @param {string} options.title - Toast title (optional)
   * @param {string} options.message - Toast message
   * @param {string} options.type - Toast type: success, error, warning, info
   * @param {number} options.duration - Duration in ms (default: 5000)
   * @param {boolean} options.dismissible - Show close button (default: true)
   */
  DC.showToast = function(options) {
    const {
      title = '',
      message = '',
      type = 'info',
      duration = 5000,
      dismissible = true
    } = options;

    const container = initContainer();
    const config = TOAST_TYPES[type] || TOAST_TYPES.info;

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'modern-toast';
    toast.setAttribute('role', 'status');
    
    // Dark theme detection
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
                   (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);

    // Toast styling
    Object.assign(toast.style, {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px',
      padding: '16px',
      backgroundColor: isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
      borderLeft: `4px solid ${config.color}`,
      borderRadius: '8px',
      boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15), 0 4px 6px rgba(0, 0, 0, 0.1)',
      backdropFilter: 'blur(10px)',
      transform: 'translateX(450px)',
      opacity: '0',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      pointerEvents: 'auto',
      maxWidth: '100%',
      minWidth: '300px'
    });

    // Icon
    const iconWrapper = document.createElement('div');
    Object.assign(iconWrapper.style, {
      flexShrink: '0',
      width: '24px',
      height: '24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: config.color
    });
    iconWrapper.innerHTML = `<i class="fas ${config.icon}" style="font-size: 20px;"></i>`;

    // Content
    const content = document.createElement('div');
    Object.assign(content.style, {
      flex: '1',
      minWidth: '0'
    });

    if (title) {
      const titleEl = document.createElement('div');
      Object.assign(titleEl.style, {
        fontWeight: '600',
        fontSize: '15px',
        marginBottom: '4px',
        color: isDark ? '#f1f5f9' : '#1e293b',
        lineHeight: '1.4'
      });
      titleEl.textContent = title;
      content.appendChild(titleEl);
    }

    const messageEl = document.createElement('div');
    Object.assign(messageEl.style, {
      fontSize: '14px',
      color: isDark ? '#cbd5e1' : '#475569',
      lineHeight: '1.5',
      wordWrap: 'break-word'
    });
    messageEl.textContent = message;
    content.appendChild(messageEl);

    // Close button
    let closeBtn;
    if (dismissible) {
      closeBtn = document.createElement('button');
      closeBtn.setAttribute('aria-label', 'Close notification');
      closeBtn.innerHTML = '<i class="fas fa-times"></i>';
      Object.assign(closeBtn.style, {
        flexShrink: '0',
        width: '24px',
        height: '24px',
        border: 'none',
        background: 'transparent',
        color: isDark ? '#94a3b8' : '#64748b',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '4px',
        transition: 'all 0.2s',
        fontSize: '14px'
      });

      closeBtn.addEventListener('mouseenter', () => {
        closeBtn.style.backgroundColor = isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(100, 116, 139, 0.1)';
        closeBtn.style.color = config.color;
      });

      closeBtn.addEventListener('mouseleave', () => {
        closeBtn.style.backgroundColor = 'transparent';
        closeBtn.style.color = isDark ? '#94a3b8' : '#64748b';
      });

      closeBtn.addEventListener('click', () => dismissToast(toast));
    }

    // Assemble toast
    toast.appendChild(iconWrapper);
    toast.appendChild(content);
    if (closeBtn) toast.appendChild(closeBtn);

    // Add to container
    container.appendChild(toast);

    // Trigger entrance animation
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
        toast.style.opacity = '1';
      });
    });

    // Auto dismiss
    if (duration > 0) {
      setTimeout(() => dismissToast(toast), duration);
    }

    return toast;
  };

  /**
   * Dismiss a toast
   */
  function dismissToast(toast) {
    toast.style.transform = 'translateX(450px)';
    toast.style.opacity = '0';
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  /**
   * Helper methods for common toast types
   */
  DC.toast = {
    success: (message, title = 'Success') => DC.showToast({ type: 'success', title, message }),
    error: (message, title = 'Error') => DC.showToast({ type: 'error', title, message, duration: 7000 }),
    warning: (message, title = 'Warning') => DC.showToast({ type: 'warning', title, message }),
    info: (message, title = 'Info') => DC.showToast({ type: 'info', title, message })
  };

  /**
   * Handle Django messages on page load
   */
  document.addEventListener('DOMContentLoaded', function() {
    try {
      const messagesElement = document.getElementById('dj-messages');
      if (!messagesElement) return;

      const messages = JSON.parse(messagesElement.textContent || '[]');
      if (!Array.isArray(messages) || messages.length === 0) return;

      // Show each message with a slight delay for better UX
      messages.forEach((msg, index) => {
        setTimeout(() => {
          const type = msg.level || 'info';
          const title = type.charAt(0).toUpperCase() + type.slice(1);
          
          DC.showToast({
            type: type,
            title: title,
            message: msg.text || '',
            duration: type === 'error' ? 7000 : 5000
          });
        }, index * 150); // Stagger by 150ms
      });
    } catch (e) {
      console.error('Failed to process Django messages:', e);
    }
  });

  // Responsive handling
  function updateContainerPosition() {
    if (!toastContainer) return;

    if (window.innerWidth <= 640) {
      // Mobile: center at top
      Object.assign(toastContainer.style, {
        top: '10px',
        right: '10px',
        left: '10px',
        maxWidth: 'calc(100vw - 20px)'
      });
    } else {
      // Desktop: top right
      Object.assign(toastContainer.style, {
        top: '20px',
        right: '20px',
        left: 'auto',
        maxWidth: '420px'
      });
    }
  }

  window.addEventListener('resize', updateContainerPosition);
  
  // Initialize on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateContainerPosition);
  } else {
    updateContainerPosition();
  }

})();
