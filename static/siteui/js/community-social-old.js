// DeltaCrown Community Social - Interactive JavaScript

class CommunityApp {
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
        this.initInfiniteScroll();
        this.initTooltips();
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
        
        // Update theme toggle icon
        const themeToggle = document.querySelector('.theme-toggle');
        const icon = themeToggle.querySelector('.icon');
        
        if (theme === 'dark') {
            icon.innerHTML = `
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            `;
            themeToggle.setAttribute('aria-label', 'Switch to light mode');
        } else {
            icon.innerHTML = `
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            `;
            themeToggle.setAttribute('aria-label', 'Switch to dark mode');
        }
    }

    initTheme() {
        // Set initial theme
        this.setTheme(this.currentTheme);
        
        // Theme toggle click handler
        document.querySelector('.theme-toggle').addEventListener('click', () => {
            const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
            this.setTheme(newTheme);
        });
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('deltacrown-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    // Modal Management
    initModals() {
        // Modal triggers
        document.querySelectorAll('[data-modal]').forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = trigger.dataset.modal + 'Modal';
                this.openModal(modalId);
            });
        });

        // Modal close handlers
        document.querySelectorAll('[data-close-modal]').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.closeModal(closeBtn.closest('.modal'));
            });
        });

        // Close modal on overlay click
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', () => {
                this.closeModal(overlay.closest('.modal'));
            });
        });

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal.active');
                if (activeModal) {
                    this.closeModal(activeModal);
                }
            }
        });
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

    closeModal(modal) {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
            
            // Reset form if present
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
                this.resetFileUpload(form);
            }
        }
    }

    // Post Actions
    initPostActions() {
        // Like buttons
        document.querySelectorAll('.action-btn[data-action="like"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleLike(btn);
            });
        });

        // Share buttons
        document.querySelectorAll('.action-btn[data-action="share"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.sharePost(btn);
            });
        });

        // Comment buttons
        document.querySelectorAll('.action-btn[data-action="comment"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                // Scroll to comments section or open comment modal
                this.focusComments(btn);
            });
        });
    }

    async toggleLike(btn) {
        const postId = btn.dataset.postId;
        const icon = btn.querySelector('.icon');
        const isLiked = btn.classList.contains('liked');
        
        // Optimistic update
        btn.classList.toggle('liked');
        
        if (!isLiked) {
            // Add like animation
            btn.classList.add('liked');
            icon.style.animation = 'heartBeat 0.6s ease-in-out';
            setTimeout(() => {
                icon.style.animation = '';
            }, 600);
        }
        
        try {
            const response = await fetch(`/api/posts/${postId}/like/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ liked: !isLiked })
            });
            
            if (!response.ok) {
                // Revert optimistic update
                btn.classList.toggle('liked');
                throw new Error('Failed to toggle like');
            }
            
            const data = await response.json();
            this.updateLikeCount(btn, data.likes_count);
            
        } catch (error) {
            console.error('Error toggling like:', error);
            // Show error message
            this.showToast('Failed to update like. Please try again.', 'error');
        }
    }

    updateLikeCount(btn, count) {
        const statsElement = btn.closest('.post-card').querySelector('.action-stats .likes-count');
        if (statsElement) {
            statsElement.textContent = count > 0 ? `${count} ${count === 1 ? 'like' : 'likes'}` : '';
        }
    }

    async sharePost(btn) {
        const postUrl = btn.dataset.url;
        const postTitle = btn.dataset.title || 'Check out this post on DeltaCrown';
        
        if (navigator.share) {
            try {
                await navigator.share({
                    title: postTitle,
                    url: postUrl
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    this.copyToClipboard(postUrl);
                }
            }
        } else {
            this.copyToClipboard(postUrl);
        }
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Link copied to clipboard!', 'success');
        } catch (error) {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            this.showToast('Link copied to clipboard!', 'success');
        }
    }

    focusComments(btn) {
        // If on same page, scroll to comments
        const postCard = btn.closest('.post-card');
        const commentsSection = postCard.querySelector('.comments-section');
        
        if (commentsSection) {
            commentsSection.scrollIntoView({ behavior: 'smooth' });
            const commentInput = commentsSection.querySelector('textarea');
            if (commentInput) {
                setTimeout(() => commentInput.focus(), 500);
            }
        } else {
            // Navigate to post detail page
            const postUrl = btn.dataset.url;
            if (postUrl) {
                window.location.href = postUrl + '#comments';
            }
        }
    }

    // File Upload
    initFileUpload() {
        document.querySelectorAll('.file-upload-area').forEach(area => {
            const input = area.parentElement.querySelector('.file-input');
            
            area.addEventListener('click', () => input.click());
            
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('drag-over');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('drag-over');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    input.files = files;
                    this.handleFileSelect(input);
                }
            });
            
            input.addEventListener('change', () => {
                this.handleFileSelect(input);
            });
        });
    }

    handleFileSelect(input) {
        const files = Array.from(input.files);
        const previewContainer = input.parentElement.querySelector('.file-preview') ||
                                this.createFilePreview(input.parentElement);
        
        previewContainer.innerHTML = '';
        
        files.forEach((file, index) => {
            if (file.type.startsWith('image/')) {
                this.createImagePreview(file, previewContainer, index);
            } else if (file.type.startsWith('video/')) {
                this.createVideoPreview(file, previewContainer, index);
            }
        });
        
        previewContainer.style.display = files.length > 0 ? 'block' : 'none';
    }

    createFilePreview(parent) {
        const preview = document.createElement('div');
        preview.className = 'file-preview';
        preview.style.marginTop = '16px';
        parent.appendChild(preview);
        return preview;
    }

    createImagePreview(file, container, index) {
        const wrapper = document.createElement('div');
        wrapper.className = 'preview-item';
        wrapper.style.cssText = 'position: relative; display: inline-block; margin: 4px;';
        
        const img = document.createElement('img');
        img.style.cssText = 'width: 80px; height: 80px; object-fit: cover; border-radius: 8px;';
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '×';
        removeBtn.style.cssText = `
            position: absolute; top: -8px; right: -8px; width: 20px; height: 20px;
            border-radius: 50%; background: #ed4956; color: white; border: none;
            font-size: 12px; cursor: pointer; line-height: 1;
        `;
        
        removeBtn.addEventListener('click', () => {
            wrapper.remove();
            this.updateFileInput(container);
        });
        
        wrapper.appendChild(img);
        wrapper.appendChild(removeBtn);
        container.appendChild(wrapper);
        
        const reader = new FileReader();
        reader.onload = (e) => img.src = e.target.result;
        reader.readAsDataURL(file);
    }

    createVideoPreview(file, container, index) {
        const wrapper = document.createElement('div');
        wrapper.className = 'preview-item';
        wrapper.style.cssText = 'position: relative; display: inline-block; margin: 4px;';
        
        const video = document.createElement('video');
        video.style.cssText = 'width: 80px; height: 80px; object-fit: cover; border-radius: 8px;';
        video.muted = true;
        
        const overlay = document.createElement('div');
        overlay.innerHTML = '▶';
        overlay.style.cssText = `
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: white; font-size: 16px; background: rgba(0,0,0,0.5);
            width: 24px; height: 24px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
        `;
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '×';
        removeBtn.style.cssText = `
            position: absolute; top: -8px; right: -8px; width: 20px; height: 20px;
            border-radius: 50%; background: #ed4956; color: white; border: none;
            font-size: 12px; cursor: pointer; line-height: 1;
        `;
        
        removeBtn.addEventListener('click', () => {
            wrapper.remove();
            this.updateFileInput(container);
        });
        
        wrapper.appendChild(video);
        wrapper.appendChild(overlay);
        wrapper.appendChild(removeBtn);
        container.appendChild(wrapper);
        
        const reader = new FileReader();
        reader.onload = (e) => {
            video.src = e.target.result;
            video.load();
        };
        reader.readAsDataURL(file);
    }

    updateFileInput(container) {
        // This is a simplified version - in a real app you'd need to update the actual file input
        if (container.children.length === 0) {
            container.style.display = 'none';
        }
    }

    resetFileUpload(form) {
        const preview = form.querySelector('.file-preview');
        if (preview) {
            preview.innerHTML = '';
            preview.style.display = 'none';
        }
    }

    // Search functionality
    initSearch() {
        const searchForm = document.querySelector('.search-filter-content form');
        const searchInput = document.querySelector('.search-input');
        let searchTimeout;
        
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performSearch(searchInput.value);
                }, 500);
            });
        }
        
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.performSearch(searchInput.value, true);
            });
        }
    }

    performSearch(query, immediate = false) {
        const params = new URLSearchParams(window.location.search);
        
        if (query.trim()) {
            params.set('q', query.trim());
        } else {
            params.delete('q');
        }
        
        params.delete('page'); // Reset to first page
        
        const newUrl = window.location.pathname + '?' + params.toString();
        
        if (immediate) {
            window.location.href = newUrl;
        } else {
            // Update URL without reload for better UX
            history.replaceState(null, '', newUrl);
        }
    }

    // Infinite scroll (if needed)
    initInfiniteScroll() {
        const loadMoreBtn = document.querySelector('.load-more-btn');
        if (!loadMoreBtn) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadMorePosts();
                }
            });
        });
        
        observer.observe(loadMoreBtn);
    }

    async loadMorePosts() {
        // Implementation for loading more posts via AJAX
        // This would typically fetch from a paginated API endpoint
    }

    // Utility functions
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    showToast(message, type = 'info') {
        // Remove existing toast
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 1100;
            padding: 16px 20px; border-radius: 8px; color: white;
            font-weight: 500; max-width: 300px;
            transform: translateX(100%); transition: transform 0.3s ease;
        `;
        
        switch (type) {
            case 'success':
                toast.style.backgroundColor = '#22c55e';
                break;
            case 'error':
                toast.style.backgroundColor = '#ef4444';
                break;
            default:
                toast.style.backgroundColor = '#3b82f6';
        }
        
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    initTooltips() {
        // Simple tooltip implementation
        document.querySelectorAll('[title]').forEach(element => {
            let tooltip;
            
            element.addEventListener('mouseenter', (e) => {
                tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.textContent = element.title;
                tooltip.style.cssText = `
                    position: absolute; background: rgba(0, 0, 0, 0.9); color: white;
                    padding: 8px 12px; border-radius: 6px; font-size: 12px;
                    white-space: nowrap; z-index: 1000; pointer-events: none;
                `;
                
                document.body.appendChild(tooltip);
                
                const rect = element.getBoundingClientRect();
                tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
                tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
                
                // Hide original title to prevent double tooltip
                element.dataset.originalTitle = element.title;
                element.title = '';
            });
            
            element.addEventListener('mouseleave', () => {
                if (tooltip) {
                    tooltip.remove();
                    element.title = element.dataset.originalTitle || '';
                }
            });
        });
    }
}

// CSS Animation for heart beat effect
const style = document.createElement('style');
style.textContent = `
    @keyframes heartBeat {
        0% { transform: scale(1); }
        14% { transform: scale(1.3); }
        28% { transform: scale(1); }
        42% { transform: scale(1.3); }
        70% { transform: scale(1); }
    }
    
    .drag-over {
        border-color: var(--border-focus) !important;
        background-color: rgba(0, 149, 246, 0.05) !important;
    }
    
    .tooltip {
        animation: tooltipFadeIn 0.2s ease-out;
    }
    
    @keyframes tooltipFadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.communityApp = new CommunityApp();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CommunityApp;
}