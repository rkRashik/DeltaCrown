/**
 * BB8 Theme Toggle Functionality
 * Handles the Star Wars BB8-inspired theme toggle
 */

document.addEventListener('DOMContentLoaded', function() {
    const bb8Toggle = document.getElementById('theme-toggle');
    const body = document.body;
    
    if (!bb8Toggle) return;
    
    // Default to dark mode (no light mode support)
    const currentTheme = 'dark';
    
    // Apply dark theme on page load
    body.classList.add('dark-theme');
    if (bb8Toggle) {
        bb8Toggle.checked = true;
    }
    
    // Handle theme toggle (force dark mode only)
    bb8Toggle.addEventListener('change', function() {
        // Always force dark mode - prevent light mode
        body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
        this.checked = true;
        
        // Add fun BB8 animation sound effect
        playBB8Sound();
    });
    
    // Optional: BB8 beep sound effect
    function playBB8Sound() {
        // Create a subtle beep sound using Web Audio API
        if (window.AudioContext || window.webkitAudioContext) {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.type = 'sine';
                oscillator.frequency.value = 800; // BB8-like frequency
                
                gainNode.gain.value = 0.1; // Low volume
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.1);
            } catch (error) {
                // Silently fail if audio is not supported or blocked
            }
        }
    }
    
    // Add hover effects for BB8 animation
    bb8Toggle.addEventListener('mouseenter', function() {
        this.closest('.bb8-toggle').style.transform = 'scale(0.85)';
    });
    
    bb8Toggle.addEventListener('mouseleave', function() {
        this.closest('.bb8-toggle').style.transform = 'scale(0.8)';
    });
});