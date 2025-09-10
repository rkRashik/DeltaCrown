(function(){
  // Home-specific light touches (rely on motion.js for countdown/reveal/count-up)
  // Ensure shine animation is paused for reduced motion
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll('.shine').forEach(el => el.style.display = 'none');
  }
})();

