// Premium Community Hub - Interactive JavaScript

class PremiumCommunityApp {
    constructor() {
        this.currentTheme = this.getStoredTheme();
        this.init();
    }

    init() {
        this.initTheme();
        this.initModals();
        this.initPostActions();
        this.initFileUpload();
        this.initSearch();
        this.initScrollEffects();
        this.initPostCreation();
        dcLog('Premium Community Hub initialized');
    }

    // Theme Management
    getStoredTheme() {
        const stored = localStorage.getItem('deltacrown-theme');
        if (stored) return stored;
        
        // Auto-detect system theme
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('deltacrown-theme', theme);
        
        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    initTheme() {
        // Set initial theme
        this.setTheme(this.currentTheme);
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('deltacrown-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
        
        // Theme toggle handler (if exists)
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
                this.setTheme(newTheme);
            });
        }
    }

    // Modal Management
    initModals() {
        // Create Post Modal
        const createPostBtns = document.querySelectorAll('[data-modal="createPost"]');
        const modal = document.getElementById('createPostModal');
        
        if (modal) {
            createPostBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.openModal('createPostModal');
                });
            });

            // Close modal handlers
            modal.querySelectorAll('[data-close-modal]').forEach(closeBtn => {
                closeBtn.addEventListener('click', () => {
                    this.closeModal('createPostModal');
                });
            });

            // Close on backdrop click
            modal.querySelector('.modal-overlay')?.addEventListener('click', () => {
                this.closeModal('createPostModal');
            });
        }
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // Focus first input
            const firstInput = modal.querySelector('input, textarea');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    // Post Actions
    initPostActions() {
        document.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('.action-btn[data-action]');
            if (!actionBtn) return;

            const action = actionBtn.dataset.action;
            const postId = actionBtn.dataset.postId;

            switch (action) {
                case 'like':
                    this.handleLike(postId, actionBtn);
                    break;
                case 'comment':
                    this.handleComment(actionBtn);
                    break;
                case 'share':
                    this.handleShare(actionBtn);
                    break;
            }
        });
    }

    async handleLike(postId, btn) {
        try {
            // Add loading state
            btn.disabled = true;
            btn.classList.add('loading');

            // Simulate API call (replace with actual endpoint)
            await this.simulateApiCall();

            // Toggle like state
            const isLiked = btn.classList.toggle('liked');
            const icon = btn.querySelector('svg path');
            
            if (isLiked) {
                icon.setAttribute('fill', 'currentColor');
                btn.style.color = '#e91e63';
            } else {
                icon.setAttribute('fill', 'none');
                btn.style.color = '';
            }

            // Update like count (if exists)
            const likesCount = btn.closest('.post-actions').querySelector('.likes-count');
            if (likesCount) {
                const currentCount = parseInt(likesCount.textContent) || 0;
                const newCount = isLiked ? currentCount + 1 : currentCount - 1;
                likesCount.textContent = `${newCount} ${newCount === 1 ? 'like' : 'likes'}`;
            }

        } catch (error) {
            console.error('Error liking post:', error);
            this.showNotification('Failed to like post', 'error');
        } finally {
            btn.disabled = false;
            btn.classList.remove('loading');
        }
    }

    handleComment(btn) {
        const url = btn.dataset.url;
        if (url) {
            window.location.href = url;
        }
    }

    async handleShare(btn) {
        const url = btn.dataset.url;
        const title = btn.dataset.title;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: title,
                    url: url
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    this.fallbackShare(url);
                }
            }
        } else {
            this.fallbackShare(url);
        }
    }

    fallbackShare(url) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(() => {
                this.showNotification('Link copied to clipboard!', 'success');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showNotification('Link copied to clipboard!', 'success');
        }
    }

    // File Upload
    initFileUpload() {
        const fileInputs = document.querySelectorAll('.file-input');
        
        fileInputs.forEach(input => {
            const uploadArea = input.nextElementSibling;
            
            // Click to upload
            uploadArea.addEventListener('click', () => input.click());
            
            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length) {
                    input.files = files;
                    this.handleFileSelection(input, files);
                }
            });
            
            // File selection
            input.addEventListener('change', (e) => {
                this.handleFileSelection(input, e.target.files);
            });
        });
    }

    handleFileSelection(input, files) {
        const uploadArea = input.nextElementSibling;
        const fileCount = files.length;
        
        if (fileCount > 0) {
            const text = uploadArea.querySelector('p');
            text.textContent = `${fileCount} file${fileCount > 1 ? 's' : ''} selected`;
            uploadArea.classList.add('has-files');
            
            // Show file previews
            this.showFilePreview(files, input.closest('.file-upload'));
        }
    }

    showFilePreview(files, container) {
        let previewContainer = container.querySelector('.file-preview');
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'file-preview';
            previewContainer.id = 'filePreview';
            container.appendChild(previewContainer);
        }

        previewContainer.innerHTML = '';

        Array.from(files).forEach((file, index) => {
            if (file.type.startsWith('image/')) {
                const previewItem = document.createElement('div');
                previewItem.className = 'file-preview-item';

                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.onload = () => URL.revokeObjectURL(img.src);

                const removeBtn = document.createElement('button');
                removeBtn.className = 'file-preview-remove';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = (e) => {
                    e.preventDefault();
                    this.removeFileFromInput(container.querySelector('.file-input'), index);
                };

                previewItem.appendChild(img);
                previewItem.appendChild(removeBtn);
                previewContainer.appendChild(previewItem);
            }
        });
    }

    removeFileFromInput(input, indexToRemove) {
        const dt = new DataTransfer();
        const files = input.files;

        for (let i = 0; i < files.length; i++) {
            if (i !== indexToRemove) {
                dt.items.add(files[i]);
            }
        }

        input.files = dt.files;
        this.handleFileSelection(input, dt.files);
    }

    // Post Creation
    initPostCreation() {
        const postForm = document.querySelector('#createPostModal form');
        
        if (postForm) {
            postForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handlePostSubmission(postForm);
            });
        }
    }

    async handlePostSubmission(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        // Disable submit button and show loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<svg class="loading-spinner" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"></circle><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Creating...';
        
        try {
            const formData = new FormData(form);
            
            // Validate required fields
            const content = formData.get('content');
            if (!content || content.trim().length === 0) {
                throw new Error('Content is required');
            }

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showNotification(data.message || 'Post created successfully!', 'success');
                
                // Reset form
                form.reset();
                const filePreview = form.querySelector('.file-preview');
                if (filePreview) {
                    filePreview.innerHTML = '';
                }
                
                // Close modal
                this.closeModal('createPostModal');
                
                // Optionally redirect or refresh
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                }
            } else {
                throw new Error(data.error || 'Failed to create post');
            }
        } catch (error) {
            console.error('Post creation error:', error);
            this.showNotification(error.message || 'Failed to create post', 'error');
        } finally {
            // Restore submit button
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    // Search Functionality
    initSearch() {
        const searchForm = document.querySelector('.search-form');
        const searchInput = document.querySelector('.premium-search-input');
        
        if (searchForm && searchInput) {
            // Auto-submit on filter change
            const gameFilter = searchForm.querySelector('.game-filter');
            if (gameFilter) {
                gameFilter.addEventListener('change', () => {
                    searchForm.submit();
                });
            }

            // Debounced search
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    if (e.target.value.length >= 3 || e.target.value.length === 0) {
                        // Could implement live search here
                    }
                }, 300);
            });
        }
    }

    // Scroll Effects
    initScrollEffects() {
        const searchSection = document.querySelector('.premium-search-section');
        
        if (searchSection) {
            let lastScrollTop = 0;
            
            window.addEventListener('scroll', () => {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                
                // Add/remove shadow based on scroll
                if (scrollTop > 10) {
                    searchSection.style.boxShadow = 'var(--shadow-medium)';
                } else {
                    searchSection.style.boxShadow = '';
                }
                
                lastScrollTop = scrollTop;
            });
        }

        // Infinite scroll for posts (if needed)
        this.initInfiniteScroll();
    }

    initInfiniteScroll() {
        const loadMoreTrigger = document.querySelector('.pagination-nav');
        
        if (loadMoreTrigger) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Could implement auto-loading here
                        // For now, we'll keep manual pagination
                    }
                });
            }, {
                threshold: 0.1
            });
            
            observer.observe(loadMoreTrigger);
        }
    }

    // Utility Methods
    async simulateApiCall(delay = 500) {
        return new Promise(resolve => setTimeout(resolve, delay));
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: type === 'success' ? 'var(--success-green)' : 
                       type === 'error' ? 'var(--danger-red)' : 'var(--primary-blue)',
            color: 'white',
            padding: '12px 20px',
            borderRadius: '8px',
            boxShadow: 'var(--shadow-heavy)',
            zIndex: '10000',
            transform: 'translateX(400px)',
            transition: 'transform 0.3s ease'
        });
        
        document.body.appendChild(notification);
        
        // Animate in
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
        });
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    // Enhanced interactions
    initEnhancedInteractions() {
        // Hover effects for cards
        const postCards = document.querySelectorAll('.post-card');
        postCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-2px)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });

        // Ripple effect for buttons
        const buttons = document.querySelectorAll('.action-btn, .btn-primary, .follow-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', this.createRipple);
        });
    }

    createRipple(e) {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        const ripple = document.createElement('span');
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            pointer-events: none;
        `;
        
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.communityApp = new PremiumCommunityApp();
});

// Add CSS for ripple animation
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    .drag-over {
        background: var(--bg-accent) !important;
        border-color: var(--primary-blue) !important;
    }
    
    .has-files {
        background: var(--success-green) !important;
        color: white !important;
        border-color: var(--success-green) !important;
    }
    
    .loading {
        opacity: 0.6;
        pointer-events: none;
    }
    
    .liked {
        animation: likeAnimation 0.3s ease;
    }
    
    @keyframes likeAnimation {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); }
    }
`;
document.head.appendChild(style);