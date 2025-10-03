/**
 * UI/UX Phase D: Visual Polish JavaScript Utilities
 * 
 * Features:
 * - Skeleton screen manager
 * - Toast notifications
 * - Image lazy loading with blur-up
 * - Tooltip system
 * - Stagger animations
 * - Alert manager
 * - Form validation with animations
 * 
 * @version 1.0.0
 * @author DeltaCrown Dev Team
 */

(function() {
    'use strict';

    /* ============================================
       1. Skeleton Screen Manager
       ============================================ */

    class SkeletonManager {
        static show(container, type = 'default', count = 1) {
            const skeletons = [];

            for (let i = 0; i < count; i++) {
                const skeleton = this.create(type);
                container.appendChild(skeleton);
                skeletons.push(skeleton);
            }

            return skeletons;
        }

        static create(type) {
            const templates = {
                'default': `
                    <div class="skeleton-card">
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text" style="width: 80%"></div>
                    </div>
                `,
                'tournament-card': `
                    <div class="skeleton-tournament-card">
                        <div class="skeleton skeleton-image"></div>
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text" style="width: 60%"></div>
                        <div style="display: flex; gap: 12px; margin-top: 12px;">
                            <div class="skeleton skeleton-button"></div>
                            <div class="skeleton skeleton-button"></div>
                        </div>
                    </div>
                `,
                'user-profile': `
                    <div class="skeleton-card" style="display: flex; align-items: center; gap: 16px;">
                        <div class="skeleton skeleton-avatar large"></div>
                        <div style="flex: 1;">
                            <div class="skeleton skeleton-title" style="width: 200px;"></div>
                            <div class="skeleton skeleton-text" style="width: 150px;"></div>
                        </div>
                    </div>
                `,
                'list-item': `
                    <div style="display: flex; align-items: center; gap: 12px; padding: 12px; margin-bottom: 8px;">
                        <div class="skeleton skeleton-avatar"></div>
                        <div style="flex: 1;">
                            <div class="skeleton skeleton-text"></div>
                            <div class="skeleton skeleton-text small" style="width: 60%;"></div>
                        </div>
                    </div>
                `
            };

            const wrapper = document.createElement('div');
            wrapper.innerHTML = templates[type] || templates['default'];
            wrapper.classList.add('skeleton-wrapper');
            
            return wrapper.firstElementChild;
        }

        static hide(skeletons) {
            skeletons.forEach(skeleton => {
                skeleton.style.opacity = '0';
                setTimeout(() => skeleton.remove(), 300);
            });
        }

        static replace(skeletons, content) {
            const container = skeletons[0].parentElement;
            this.hide(skeletons);
            
            setTimeout(() => {
                if (typeof content === 'string') {
                    container.innerHTML = content;
                } else {
                    container.appendChild(content);
                }
                
                // Add fade-in animation
                const newContent = container.children[container.children.length - 1];
                if (newContent) {
                    newContent.classList.add('fade-in');
                }
            }, 300);
        }
    }

    /* ============================================
       2. Toast Notification System
       ============================================ */

    class Toast {
        static container = null;

        static init() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.className = 'toast-container';
                this.container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    pointer-events: none;
                `;
                document.body.appendChild(this.container);
            }
        }

        static show(message, type = 'info', duration = 5000) {
            this.init();

            const toast = document.createElement('div');
            toast.className = `toast toast-${type} slide-in-up`;
            toast.style.cssText = `
                padding: 16px 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 300px;
                max-width: 500px;
                pointer-events: auto;
                border-left: 4px solid ${this.getColor(type)};
            `;

            const icon = this.getIcon(type);
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '×';
            closeBtn.style.cssText = `
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                opacity: 0.6;
                margin-left: auto;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            `;

            toast.innerHTML = `
                <span style="font-size: 20px;">${icon}</span>
                <span style="flex: 1;">${message}</span>
            `;
            toast.appendChild(closeBtn);

            this.container.appendChild(toast);

            // Auto-dismiss
            const dismiss = () => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            };

            closeBtn.addEventListener('click', dismiss);

            if (duration > 0) {
                setTimeout(dismiss, duration);
            }

            return toast;
        }

        static success(message, duration) {
            return this.show(message, 'success', duration);
        }

        static error(message, duration) {
            return this.show(message, 'error', duration);
        }

        static warning(message, duration) {
            return this.show(message, 'warning', duration);
        }

        static info(message, duration) {
            return this.show(message, 'info', duration);
        }

        static getColor(type) {
            const colors = {
                success: '#10b981',
                error: '#ef4444',
                warning: '#f59e0b',
                info: '#3b82f6'
            };
            return colors[type] || colors.info;
        }

        static getIcon(type) {
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };
            return icons[type] || icons.info;
        }
    }

    /* ============================================
       3. Image Lazy Loading with Blur-Up
       ============================================ */

    class LazyImageLoader {
        constructor() {
            this.observer = null;
            this.init();
        }

        init() {
            if ('IntersectionObserver' in window) {
                this.observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.loadImage(entry.target);
                        }
                    });
                }, {
                    rootMargin: '50px'
                });

                this.observe();
            } else {
                // Fallback: Load all images immediately
                this.loadAll();
            }
        }

        observe() {
            const images = document.querySelectorAll('img[data-src]:not([data-lazy-loaded])');
            images.forEach(img => this.observer.observe(img));
        }

        loadImage(img) {
            const src = img.getAttribute('data-src');
            if (!src) return;

            img.classList.add('image-blur-up');

            const tempImage = new Image();
            tempImage.onload = () => {
                img.src = src;
                img.classList.add('loaded');
                img.setAttribute('data-lazy-loaded', 'true');
                this.observer.unobserve(img);
            };
            tempImage.onerror = () => {
                img.src = img.getAttribute('data-fallback') || '/static/images/placeholder.jpg';
                img.setAttribute('data-lazy-loaded', 'true');
                this.observer.unobserve(img);
            };
            tempImage.src = src;
        }

        loadAll() {
            const images = document.querySelectorAll('img[data-src]');
            images.forEach(img => this.loadImage(img));
        }

        refresh() {
            if (this.observer) {
                this.observe();
            }
        }
    }

    /* ============================================
       4. Tooltip System
       ============================================ */

    class Tooltip {
        static init() {
            document.addEventListener('mouseover', (e) => {
                const target = e.target.closest('[data-tooltip]');
                if (target) {
                    this.show(target);
                }
            });

            document.addEventListener('mouseout', (e) => {
                const target = e.target.closest('[data-tooltip]');
                if (target) {
                    this.hide();
                }
            });
        }

        static show(element) {
            const text = element.getAttribute('data-tooltip');
            if (!text) return;

            // Remove existing tooltip
            this.hide();

            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip show';
            tooltip.textContent = text;
            tooltip.id = 'active-tooltip';

            document.body.appendChild(tooltip);

            // Position tooltip
            const rect = element.getBoundingClientRect();
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
            tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
        }

        static hide() {
            const tooltip = document.getElementById('active-tooltip');
            if (tooltip) {
                tooltip.classList.remove('show');
                setTimeout(() => tooltip.remove(), 200);
            }
        }
    }

    /* ============================================
       5. Stagger Animation Controller
       ============================================ */

    class StaggerAnimation {
        static observe(container, className = 'stagger-fade-in') {
            if ('IntersectionObserver' in window) {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add(className);
                            observer.unobserve(entry.target);
                        }
                    });
                }, {
                    threshold: 0.1
                });

                observer.observe(container);
            } else {
                container.classList.add(className);
            }
        }

        static applyToElements(selector, className = 'stagger-fade-in') {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                this.observe(element, className);
            });
        }
    }

    /* ============================================
       6. Alert Manager
       ============================================ */

    class AlertManager {
        static show(message, type = 'info', container = null, dismissable = true) {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}${dismissable ? ' alert-dismissable' : ''}`;

            const icon = this.getIcon(type);
            alert.innerHTML = `
                <span class="alert-icon">${icon}</span>
                <span class="alert-message">${message}</span>
                ${dismissable ? '<button class="alert-close" aria-label="Close">×</button>' : ''}
            `;

            if (!container) {
                container = document.querySelector('.alert-container') || document.body;
            }

            container.insertBefore(alert, container.firstChild);

            if (dismissable) {
                const closeBtn = alert.querySelector('.alert-close');
                closeBtn.addEventListener('click', () => this.dismiss(alert));

                // Auto-dismiss after 5 seconds
                setTimeout(() => this.dismiss(alert), 5000);
            }

            return alert;
        }

        static dismiss(alert) {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => alert.remove(), 300);
        }

        static success(message, container, dismissable) {
            return this.show(message, 'success', container, dismissable);
        }

        static error(message, container, dismissable) {
            return this.show(message, 'error', container, dismissable);
        }

        static warning(message, container, dismissable) {
            return this.show(message, 'warning', container, dismissable);
        }

        static info(message, container, dismissable) {
            return this.show(message, 'info', container, dismissable);
        }

        static getIcon(type) {
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };
            return icons[type] || icons.info;
        }
    }

    /* ============================================
       7. Form Validation with Animations
       ============================================ */

    class FormValidator {
        constructor(form) {
            this.form = form;
            this.init();
        }

        init() {
            this.form.addEventListener('submit', (e) => this.validate(e));

            // Real-time validation
            const inputs = this.form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => this.validateField(input));
                input.addEventListener('input', () => this.clearError(input));
            });
        }

        validate(e) {
            e.preventDefault();
            let isValid = true;

            const inputs = this.form.querySelectorAll('input[required], select[required], textarea[required]');
            inputs.forEach(input => {
                if (!this.validateField(input)) {
                    isValid = false;
                }
            });

            if (isValid) {
                this.form.submit();
            } else {
                // Shake the form
                this.form.classList.add('shake');
                setTimeout(() => this.form.classList.remove('shake'), 500);
            }

            return isValid;
        }

        validateField(input) {
            const group = input.closest('.form-group');
            if (!group) return true;

            this.clearError(input);

            // Check required
            if (input.hasAttribute('required') && !input.value.trim()) {
                this.showError(input, 'This field is required');
                return false;
            }

            // Check email
            if (input.type === 'email' && input.value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(input.value)) {
                    this.showError(input, 'Please enter a valid email');
                    return false;
                }
            }

            // Check min length
            const minLength = input.getAttribute('minlength');
            if (minLength && input.value.length < parseInt(minLength)) {
                this.showError(input, `Minimum ${minLength} characters required`);
                return false;
            }

            // Success state
            group.classList.add('success');
            setTimeout(() => group.classList.remove('success'), 2000);

            return true;
        }

        showError(input, message) {
            const group = input.closest('.form-group');
            if (!group) return;

            group.classList.add('error');
            
            // Add error message if not exists
            let errorMsg = group.querySelector('.form-error-message');
            if (!errorMsg) {
                errorMsg = document.createElement('span');
                errorMsg.className = 'form-error-message';
                input.parentNode.appendChild(errorMsg);
            }

            errorMsg.textContent = message;
            errorMsg.classList.add('shake');

            // Shake animation
            input.classList.add('shake');
            setTimeout(() => input.classList.remove('shake'), 500);
        }

        clearError(input) {
            const group = input.closest('.form-group');
            if (!group) return;

            group.classList.remove('error', 'success');
            
            const errorMsg = group.querySelector('.form-error-message');
            if (errorMsg) {
                errorMsg.remove();
            }
        }
    }

    /* ============================================
       8. Progress Bar Controller
       ============================================ */

    class ProgressBar {
        constructor(element) {
            this.container = element;
            this.fill = element.querySelector('.progress-bar-fill');
            this.currentValue = 0;
        }

        setValue(value) {
            this.currentValue = Math.max(0, Math.min(100, value));
            if (this.fill) {
                this.fill.style.width = `${this.currentValue}%`;
            }
        }

        increment(amount = 10) {
            this.setValue(this.currentValue + amount);
        }

        reset() {
            this.setValue(0);
        }

        complete() {
            this.setValue(100);
        }
    }

    /* ============================================
       9. Initialize All Visual Polish Features
       ============================================ */

    function initVisualPolish() {
        console.log('[VisualPolish] Initializing...');

        // Initialize lazy image loading
        const lazyLoader = new LazyImageLoader();
        console.log('[VisualPolish] Lazy image loading initialized');

        // Initialize tooltips
        Tooltip.init();
        console.log('[VisualPolish] Tooltips initialized');

        // Initialize form validation
        document.querySelectorAll('form[data-validate]').forEach(form => {
            new FormValidator(form);
        });
        console.log('[VisualPolish] Form validation initialized');

        // Apply stagger animations
        StaggerAnimation.applyToElements('.tournament-grid', 'stagger-slide-up');
        StaggerAnimation.applyToElements('.team-list', 'stagger-fade-in');

        // Initialize progress bars
        document.querySelectorAll('.progress-bar').forEach(bar => {
            const value = bar.getAttribute('data-value');
            if (value) {
                const progressBar = new ProgressBar(bar);
                setTimeout(() => progressBar.setValue(parseInt(value)), 100);
            }
        });

        console.log('[VisualPolish] Initialization complete');
    }

    /* ============================================
       10. Export to Global Scope
       ============================================ */

    window.VisualPolish = {
        SkeletonManager,
        Toast,
        LazyImageLoader,
        Tooltip,
        StaggerAnimation,
        AlertManager,
        FormValidator,
        ProgressBar,
        init: initVisualPolish,
    };

    /* ============================================
       11. Auto-Initialize
       ============================================ */

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVisualPolish);
    } else {
        initVisualPolish();
    }

})();
