/**
 * Sun/Moon Theme Toggle Functionality
 * Handles smooth theme switching with elegant sun/moon toggle
 */

document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const profileThemeToggle = document.getElementById('profile-theme-toggle');
    const toggleLabel = document.querySelector('.theme-toggle-label');
    const body = document.body;
    
    // Use profile toggle if main toggle doesn't exist
    const activeToggle = themeToggle || profileThemeToggle;
    if (!activeToggle) return;
    
    // Check for saved theme or default to dark mode (unchecked = light, checked = dark)
    const currentTheme = localStorage.getItem('theme') || 'dark';
    
    // Apply theme on page load
    if (currentTheme === 'dark') {
        body.classList.remove('light-theme');
        body.classList.add('dark-theme');
        body.setAttribute('data-bs-theme', 'dark');
        activeToggle.checked = true;
    } else {
        body.classList.remove('dark-theme');
        body.classList.add('light-theme');
        body.setAttribute('data-bs-theme', 'light');
        activeToggle.checked = false;
    }
    
    // Handle theme toggle with smooth animations
    activeToggle.addEventListener('change', function() {
        // Add brief "processing" class for extra visual feedback
        if (toggleLabel) {
            toggleLabel.classList.add('processing');
            setTimeout(() => toggleLabel.classList.remove('processing'), 400);
        }
        
        if (this.checked) {
            // Switch to dark theme (moon)
            body.classList.remove('light-theme');
            body.classList.add('dark-theme');
            body.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            
            // Soft night sound effect
            playToggleSound([400, 300], 0.04, 'dark');
        } else {
            // Switch to light theme (sun)
            body.classList.remove('dark-theme');
            body.classList.add('light-theme');
            body.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
            
            // Bright day sound effect
            playToggleSound([800, 1000], 0.04, 'light');
        }
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
    
    // Add keyboard support for accessibility
    activeToggle.addEventListener('keydown', function(e) {
        if (e.code === 'Space' || e.code === 'Enter') {
            e.preventDefault();
            this.checked = !this.checked;
            this.dispatchEvent(new Event('change'));
        }
    });
    
    // Add smooth transition class after initial load
    setTimeout(() => {
        body.classList.add('theme-transitions-enabled');
    }, 100);
});