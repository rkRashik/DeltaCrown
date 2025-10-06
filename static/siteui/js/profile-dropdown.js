
/* ============================================
   PROFILE DROPDOWN TOGGLE FUNCTIONALITY
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    const profileBtn = document.querySelector('[data-profile-toggle]');
    const profileDropdown = document.getElementById('profileDropdown');
    const themeToggleBtn = document.getElementById('profileThemeToggle');
    
    if (profileBtn && profileDropdown) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('is-open');
            
            // Close notification dropdown if open
            const notifDropdown = document.getElementById('notificationDropdown');
            if (notifDropdown) {
                notifDropdown.classList.remove('is-open');
            }
        });
        
        // Close when clicking outside
        document.addEventListener('click', function(e) {
            if (!profileDropdown.contains(e.target) && !profileBtn.contains(e.target)) {
                profileDropdown.classList.remove('is-open');
            }
        });
    }
    
    // Theme toggle functionality
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const root = document.documentElement;
            const currentTheme = root.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            root.setAttribute('data-theme', newTheme);
            document.body.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Play sound effect
            playThemeToggleSound(newTheme);
            
            // Update body classes
            if (newTheme === 'dark') {
                document.body.classList.remove('light-theme');
                document.body.classList.add('dark-theme');
            } else {
                document.body.classList.remove('dark-theme');
                document.body.classList.add('light-theme');
            }
        });
    }
    
    function playThemeToggleSound(theme) {
        if (!window.AudioContext && !window.webkitAudioContext) return;
        
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const frequencies = theme === 'dark' ? [400, 300] : [800, 1000];
            
            frequencies.forEach((freq, index) => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.type = theme === 'dark' ? 'sine' : 'triangle';
                oscillator.frequency.setValueAtTime(freq, audioContext.currentTime + (index * 0.08));
                oscillator.frequency.exponentialRampToValueAtTime(freq * 0.7, audioContext.currentTime + 0.15 + (index * 0.08));
                
                gainNode.gain.setValueAtTime(0.04, audioContext.currentTime + (index * 0.08));
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15 + (index * 0.08));
                
                oscillator.start(audioContext.currentTime + (index * 0.08));
                oscillator.stop(audioContext.currentTime + 0.15 + (index * 0.08));
            });
        } catch (error) {
            // Silently fail
        }
    }
});
