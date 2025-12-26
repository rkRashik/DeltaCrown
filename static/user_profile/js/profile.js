/**
 * UP-UI-REBIRTH-01: Profile Page Interactions
 * Vanilla JavaScript for modern esports profile
 */

(function() {
    'use strict';
    
    // ========== UTILITIES ==========
    
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `px-6 py-4 rounded-xl text-white font-semibold shadow-2xl transform transition-all duration-300 ${
            type === 'error' ? 'bg-red-600' : 'bg-emerald-600'
        }`;
        toast.textContent = message;
        toast.style.animation = 'slideInUp 0.3s ease-out';
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    window.copyToClipboard = function(text) {
        if (!navigator.clipboard) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            try {
                document.execCommand('copy');
                showToast('Copied to clipboard!');
            } catch (err) {
                showToast('Failed to copy', 'error');
            }
            
            document.body.removeChild(textarea);
            return;
        }
        
        navigator.clipboard.writeText(text)
            .then(() => showToast('Copied to clipboard!'))
            .catch(() => showToast('Failed to copy', 'error'));
    };
    
    window.shareProfile = function() {
        const url = window.location.href;
        const title = document.querySelector('h1').textContent;
        
        if (navigator.share) {
            navigator.share({
                title: title,
                url: url
            }).catch(err => console.log('Share cancelled'));
        } else {
            copyToClipboard(url);
        }
    };
    
    function smoothScrollTo(targetId) {
        const target = document.getElementById(targetId);
        if (!target) return;
        
        const navHeight = 80;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
        
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
    
    // ========== DASHBOARD NAVIGATION ==========
    
    function initDashboardNav() {
        const navChips = document.querySelectorAll('.nav-chip');
        
        navChips.forEach(chip => {
            chip.addEventListener('click', function(e) {
                e.preventDefault();
                
                navChips.forEach(c => c.classList.remove('active'));
                this.classList.add('active');
                
                const targetId = this.getAttribute('href').substring(1);
                smoothScrollTo(targetId);
            });
        });
        
        // Intersection Observer for auto-highlighting
        const sections = Array.from(navChips).map(chip => {
            const targetId = chip.getAttribute('href').substring(1);
            return document.getElementById(targetId);
        }).filter(Boolean);
        
        const observerOptions = {
            root: null,
            rootMargin: '-100px 0px -66%',
            threshold: 0
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const activeChip = document.querySelector(`.nav-chip[href="#${entry.target.id}"]`);
                    if (activeChip) {
                        navChips.forEach(c => c.classList.remove('active'));
                        activeChip.classList.add('active');
                    }
                }
            });
        }, observerOptions);
        
        sections.forEach(section => {
            if (section) observer.observe(section);
        });
    }
    
    // ========== COLLAPSIBLE SECTIONS ==========
    
    function initCollapsible() {
        const toggleBtn = document.getElementById('toggleMoreGames');
        const content = document.getElementById('moreGamesContent');
        const icon = document.getElementById('expandIcon');
        
        if (!toggleBtn || !content) return;
        
        toggleBtn.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            
            this.setAttribute('aria-expanded', !isExpanded);
            content.setAttribute('aria-hidden', isExpanded);
            content.classList.toggle('expanded');
            
            if (icon) {
                icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
            }
        });
    }
    
    // ========== URL HASH SUPPORT ==========
    
    function handleUrlHash() {
        const hash = window.location.hash;
        if (hash && hash.length > 1) {
            const targetId = hash.substring(1);
            
            setTimeout(() => {
                smoothScrollTo(targetId);
                
                const activeChip = document.querySelector(`.nav-chip[href="${hash}"]`);
                if (activeChip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    activeChip.classList.add('active');
                }
            }, 300);
        }
    }
    
    // ========== KEYBOARD SHORTCUTS ==========
    
    function initKeyboardShortcuts() {
        const shortcuts = {
            '1': 'stats',
            '2': 'passports',
            '3': 'teams',
            '4': 'tournaments',
            '5': 'economy',
            '6': 'shop',
            '7': 'activity',
            '8': 'about'
        };
        
        document.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT' || 
                e.target.tagName === 'TEXTAREA' || 
                e.target.isContentEditable) {
                return;
            }
            
            if (e.altKey && shortcuts[e.key]) {
                e.preventDefault();
                smoothScrollTo(shortcuts[e.key]);
                
                const chip = document.querySelector(`.nav-chip[href="#${shortcuts[e.key]}"]`);
                if (chip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                }
            }
        });
    }
    
    // ========== INITIALIZATION ==========
    
    function init() {
        const bentoCard = document.querySelector('.bento-card');
        if (!bentoCard) return;
        
        console.log('Initializing Profile v3 (UP-UI-REBIRTH-01)...');
        
        try {
            initDashboardNav();
            initCollapsible();
            handleUrlHash();
            initKeyboardShortcuts();
            
            console.log('Profile initialized successfully');
        } catch (error) {
            console.error('Error initializing Profile:', error);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.addEventListener('hashchange', handleUrlHash);
    
})();

// CSS Animations
const style = document.createElement('style');
style.textContent = `
@keyframes slideInUp {
    from { transform: translateY(100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

@keyframes slideOutDown {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(100%); opacity: 0; }
}
`;
document.head.appendChild(style);
