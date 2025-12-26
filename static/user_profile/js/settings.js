/**
 * UP-UI-REBIRTH-01: Settings Hub Interactions
 * Vanilla JavaScript for settings navigation and forms
 */

(function() {
    'use strict';
    
    // ========== SECTION NAVIGATION ==========
    
    function initSectionNav() {
        const navItems = document.querySelectorAll('.settings-nav-item');
        const sections = document.querySelectorAll('.settings-section');
        
        navItems.forEach(item => {
            item.addEventListener('click', function() {
                const sectionId = this.getAttribute('data-section');
                
                // Update nav active state
                navItems.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
                
                // Show corresponding section
                sections.forEach(section => {
                    section.classList.remove('active');
                    if (section.id === `section-${sectionId}`) {
                        section.classList.add('active');
                    }
                });
                
                // Update URL hash
                window.history.pushState(null, null, `#${sectionId}`);
            });
        });
        
        // Handle direct hash navigation
        const hash = window.location.hash.substring(1);
        if (hash) {
            const navItem = document.querySelector(`[data-section="${hash}"]`);
            if (navItem) {
                navItem.click();
            }
        }
    }
    
    // ========== TOGGLE SWITCHES ==========
    
    function initToggleSwitches() {
        const toggles = document.querySelectorAll('.toggle-switch');
        
        toggles.forEach(toggle => {
            toggle.addEventListener('click', function() {
                this.classList.toggle('active');
                const setting = this.getAttribute('data-toggle');
                const isActive = this.classList.contains('active');
                
                console.log(`Toggle ${setting}: ${isActive}`);
                
                // Here you would make an AJAX call to save the setting
                // For now, just show a toast
                showToast(`Setting ${isActive ? 'enabled' : 'disabled'}`);
            });
        });
    }
    
    // ========== FORM VALIDATION ==========
    
    function initFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                console.log('Form submitted:', Object.fromEntries(formData));
                
                // Simulate save
                showToast('Settings saved successfully!');
            });
        });
        
        // Real-time validation
        const inputs = document.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.style.borderColor = 'rgb(239, 68, 68)';
                } else {
                    this.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                }
            });
        });
    }
    
    // ========== UTILITIES ==========
    
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-4 rounded-xl text-white font-semibold shadow-2xl z-50 ${
            type === 'error' ? 'bg-red-600' : 'bg-emerald-600'
        }`;
        toast.textContent = message;
        toast.style.animation = 'slideInUp 0.3s ease-out';
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // ========== INITIALIZATION ==========
    
    function init() {
        const settingsNav = document.querySelector('.settings-nav-item');
        if (!settingsNav) return;
        
        console.log('Initializing Settings Hub (UP-UI-REBIRTH-01)...');
        
        try {
            initSectionNav();
            initToggleSwitches();
            initFormValidation();
            
            console.log('Settings Hub initialized successfully');
        } catch (error) {
            console.error('Error initializing Settings:', error);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
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
