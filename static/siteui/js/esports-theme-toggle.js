/**
 * Sun/Moon Theme Toggle Functionality
 * Handles smooth theme switching with elegant sun/moon toggle
 * Works with profile dropdown and all theme toggle buttons
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find all theme toggles
    const themeToggles = document.querySelectorAll('[data-theme-toggle]');
    const root = document.documentElement;
    const body = document.body;
    
    // Default to dark mode always (no light mode)
    const currentTheme = localStorage.getItem('theme') || 'dark';
    
    // Apply theme on page load
    function applyTheme(theme) {
        // Force dark mode - no light mode support
        const finalTheme = 'dark';
        
        body.classList.remove('light-theme');
        body.classList.add('dark-theme');
        root.setAttribute('data-theme', 'dark');
        body.setAttribute('data-bs-theme', 'dark');
        
        // Update all toggles to checked (dark mode)
        themeToggles.forEach(toggle => {
            toggle.checked = true;
        });
    }
    
    // Apply initial theme
    applyTheme(currentTheme);
    
    // Handle theme toggle change (force dark mode only)
    themeToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            // Always force dark mode - no light mode allowed
            const newTheme = 'dark';
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Keep all toggles checked (dark mode)
            themeToggles.forEach(otherToggle => {
                otherToggle.checked = true;
            });
            
            // Play sound effect for dark mode
            playToggleSound([400, 300], 0.04, 'dark');
        });
        
        // Keyboard support
        toggle.addEventListener('keydown', function(e) {
            if (e.code === 'Space' || e.code === 'Enter') {
                e.preventDefault();
                this.checked = !this.checked;
                this.dispatchEvent(new Event('change'));
            }
        });
    });
    
    // Subtle toggle sound effect
    function playToggleSound(frequencies, volume, theme) {
        if (!window.AudioContext && !window.webkitAudioContext) return;
        
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            frequencies.forEach((freq, index) => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.type = theme === 'dark' ? 'sine' : 'triangle';
                oscillator.frequency.setValueAtTime(freq, audioContext.currentTime + (index * 0.08));
                oscillator.frequency.exponentialRampToValueAtTime(freq * 0.7, audioContext.currentTime + 0.15 + (index * 0.08));
                
                gainNode.gain.setValueAtTime(volume, audioContext.currentTime + (index * 0.08));
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15 + (index * 0.08));
                
                oscillator.start(audioContext.currentTime + (index * 0.08));
                oscillator.stop(audioContext.currentTime + 0.15 + (index * 0.08));
            });
        } catch (error) {
            // Silently fail if audio is not supported or blocked
        }
    }
    
    // Add smooth transition class after initial load
    setTimeout(() => {
        body.classList.add('theme-transitions-enabled');
    }, 100);
});