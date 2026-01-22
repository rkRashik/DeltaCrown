/**
 * DeltaCrown Modern Toast Notification System
 * 2026 standard-grade toast messages with animations and icons
 */

class ToastManager {
    constructor() {
        this.container = this.createContainer();
        document.body.appendChild(this.container);
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'dc-toast-container';
        container.className = 'fixed top-4 right-4 z-[9999] space-y-3 pointer-events-none';
        container.style.cssText = `
            max-width: 420px;
            width: 100%;
        `;
        // Assign to instance and return
        this.container = container;
        return container;
    }

    show(message, type = 'info', duration = 4000) {
        const toast = this.createToast(message, type);
        this.container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('dc-toast--show');
        });

        // Auto remove
        setTimeout(() => {
            this.remove(toast);
        }, duration);

        return toast;
    }

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `dc-toast dc-toast--${type}`;
        
        const config = this.getTypeConfig(type);
        
        toast.innerHTML = `
            <div class="dc-toast__icon">
                <i class="${config.icon}"></i>
            </div>
            <div class="dc-toast__content">
                <div class="dc-toast__message">${this.escapeHtml(message)}</div>
            </div>
            <button class="dc-toast__close" onclick="window.DCToast.remove(this.parentElement)">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;

        // Allow interactions on toast (close button)
        toast.style.pointerEvents = 'auto';

        return toast;
    }

    getTypeConfig(type) {
        const configs = {
            success: {
                icon: 'fa-solid fa-circle-check',
                color: '#10b981'
            },
            error: {
                icon: 'fa-solid fa-circle-xmark',
                color: '#ef4444'
            },
            warning: {
                icon: 'fa-solid fa-triangle-exclamation',
                color: '#f59e0b'
            },
            info: {
                icon: 'fa-solid fa-circle-info',
                color: '#3b82f6'
            }
        };
        return configs[type] || configs.info;
    }

    remove(toast) {
        if (typeof toast === 'string') {
            toast = document.getElementById(toast);
        }
        if (!toast) return;

        toast.classList.remove('dc-toast--show');
        toast.classList.add('dc-toast--hide');

        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// Initialize global toast manager
window.DCToast = new ToastManager();

// Backward compatibility
window.showToast = function(options) {
    if (typeof options === 'string') {
        window.DCToast.info(options);
    } else {
        const type = options.type || 'info';
        const message = options.message || options.text || '';
        const duration = options.duration || 4000;
        window.DCToast.show(message, type, duration);
    }
};

// Add toast styles dynamically
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .dc-toast {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: rgba(17, 24, 39, 0.95);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3),
                    0 10px 10px -5px rgba(0, 0, 0, 0.2);
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 14px;
        line-height: 1.5;
        transform: translateX(calc(100% + 20px));
        opacity: 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        pointer-events: auto;
    }

    .dc-toast--show {
        transform: translateX(0);
        opacity: 1;
    }

    .dc-toast--hide {
        transform: translateX(calc(100% + 20px));
        opacity: 0;
    }

    .dc-toast__icon {
        flex-shrink: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-center;
        font-size: 20px;
    }

    .dc-toast--success .dc-toast__icon {
        color: #10b981;
    }

    .dc-toast--error .dc-toast__icon {
        color: #ef4444;
    }

    .dc-toast--warning .dc-toast__icon {
        color: #f59e0b;
    }

    .dc-toast--info .dc-toast__icon {
        color: #3b82f6;
    }

    .dc-toast__content {
        flex: 1;
        min-width: 0;
    }

    .dc-toast__message {
        color: rgba(255, 255, 255, 0.9);
        word-break: break-word;
    }

    .dc-toast__close {
        flex-shrink: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        color: rgba(255, 255, 255, 0.5);
        cursor: pointer;
        border-radius: 6px;
        transition: all 0.2s;
        padding: 0;
    }

    .dc-toast__close:hover {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.9);
    }

    @media (max-width: 640px) {
        #dc-toast-container {
            left: 16px;
            right: 16px;
            top: 16px;
            max-width: none;
        }
        
        .dc-toast {
            padding: 14px;
            font-size: 13px;
        }
    }
`;
document.head.appendChild(toastStyles);
