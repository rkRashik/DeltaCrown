(function(){
  // Lightweight micro-interactions beyond motion.js if needed
  // Example: add hover shine effect re-trigger
  document.querySelectorAll('.spotlight-card').forEach(card => {
    card.addEventListener('mousemove', () => {
      const s = card.querySelector('.shine'); if (!s) return;
      s.style.animation = 'none'; s.offsetHeight; s.style.animation = '';
    });
  });
})();

// Toast system moved to notifications.js for better organization and features

