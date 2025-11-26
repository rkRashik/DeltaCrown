/**
 * DeltaCrown Settings Page - Interactive Features
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Section Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.settings-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const targetSection = this.dataset.section;
            
            // Update active nav item
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            // Update active section
            sections.forEach(section => section.classList.remove('active'));
            const activeSection = document.getElementById(`section-${targetSection}`);
            if (activeSection) {
                activeSection.classList.add('active');
                
                // Scroll to top of section smoothly
                activeSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            
            // Update URL hash without jumping
            if (history.pushState) {
                history.pushState(null, null, `#${targetSection}`);
            }
        });
    });
    
    // Handle initial hash on page load
    function handleInitialHash() {
        const hash = window.location.hash.slice(1);
        if (hash) {
            const targetNav = document.querySelector(`.nav-item[data-section="${hash}"]`);
            if (targetNav) {
                targetNav.click();
            }
        }
    }
    
    handleInitialHash();
    
    // File Input Preview
    const avatarInput = document.getElementById('avatar-input');
    if (avatarInput) {
        avatarInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.querySelector('.avatar-preview');
                    if (preview) {
                        if (preview.tagName === 'IMG') {
                            preview.src = e.target.result;
                        } else {
                            const img = document.createElement('img');
                            img.src = e.target.result;
                            img.className = 'avatar-preview';
                            preview.replaceWith(img);
                        }
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    const bannerInput = document.getElementById('banner-input');
    if (bannerInput) {
        bannerInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.querySelector('.banner-preview');
                    if (preview) {
                        if (preview.tagName === 'IMG') {
                            preview.src = e.target.result;
                        } else {
                            const img = document.createElement('img');
                            img.src = e.target.result;
                            img.className = 'banner-preview';
                            preview.replaceWith(img);
                        }
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Form Validation
    const forms = document.querySelectorAll('.settings-form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add your custom validation here
            const inputs = this.querySelectorAll('.form-input[required]');
            let isValid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = 'var(--danger)';
                } else {
                    input.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    });
    
    // Character Counter for Bio
    const bioTextarea = document.getElementById('bio');
    if (bioTextarea) {
        const maxLength = 500;
        const hint = bioTextarea.nextElementSibling;
        
        function updateCounter() {
            const remaining = maxLength - bioTextarea.value.length;
            if (hint && hint.classList.contains('form-hint')) {
                hint.textContent = `${remaining} characters remaining`;
                if (remaining < 50) {
                    hint.style.color = 'var(--danger)';
                } else {
                    hint.style.color = '';
                }
            }
        }
        
        bioTextarea.addEventListener('input', updateCounter);
        updateCounter();
    }
    
    // Unsaved Changes Warning
    let formChanged = false;
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                formChanged = true;
            });
        });
        
        form.addEventListener('submit', () => {
            formChanged = false;
        });
    });
    
    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
    
    // Privacy Toggle Animations
    const checkboxLabels = document.querySelectorAll('.checkbox-label');
    checkboxLabels.forEach(label => {
        const checkbox = label.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.addEventListener('change', function() {
                label.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    label.style.transform = '';
                }, 150);
            });
        }
    });
    
    // Smooth Scroll for Navigation
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // Auto-save Draft (Optional feature)
    let autoSaveTimeout;
    function autoSaveDraft() {
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = setTimeout(() => {
            // Collect form data
            const formData = {};
            forms.forEach(form => {
                const inputs = form.querySelectorAll('input:not([type="file"]), textarea, select');
                inputs.forEach(input => {
                    if (input.name) {
                        formData[input.name] = input.value;
                    }
                });
            });
            
            // Save to localStorage
            try {
                localStorage.setItem('settings_draft', JSON.stringify(formData));
                console.log('Draft saved');
            } catch (e) {
                console.error('Failed to save draft:', e);
            }
        }, 2000);
    }
    
    // Restore Draft on Load
    function restoreDraft() {
        try {
            const draft = localStorage.getItem('settings_draft');
            if (draft) {
                const formData = JSON.parse(draft);
                Object.keys(formData).forEach(name => {
                    const input = document.querySelector(`[name="${name}"]`);
                    if (input && input.type !== 'file') {
                        input.value = formData[name];
                    }
                });
            }
        } catch (e) {
            console.error('Failed to restore draft:', e);
        }
    }
    
    // Enable auto-save on input
    forms.forEach(form => {
        form.addEventListener('input', autoSaveDraft);
    });
    
    // Clear draft on successful submit
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            localStorage.removeItem('settings_draft');
        });
    });
    
    // Restore draft if available
    // restoreDraft(); // Uncomment to enable draft restoration
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const activeSection = document.querySelector('.settings-section.active');
            if (activeSection) {
                const form = activeSection.querySelector('form');
                if (form) {
                    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                }
            }
        }
    });
    
    // Password strength indicator (if password field exists)
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            // Add visual indicator here
        });
    });
    
    function calculatePasswordStrength(password) {
        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        return strength;
    }
    
    // Add loading state to submit buttons
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Saving...';
                submitBtn.style.opacity = '0.7';
            }
        });
    });
    
});
