// Arena Watch Page JavaScript
// Handles video modal functionality and keyboard shortcuts for the watch page

(function(){
  // Focus search with "/"
  document.addEventListener('keydown', (e)=>{
    if (e.key === '/' && !e.target.matches('input, textarea')) {
      const q = document.getElementById('q'); 
      if(q){ 
        e.preventDefault(); 
        q.focus(); 
      }
    }
  });

  // Modal embed opener
  const modal = document.getElementById('watch-modal');
  const iframe = document.getElementById('watch-iframe');
  document.querySelectorAll('[data-open-watch]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const url = btn.getAttribute('data-embed-url');
      if (!url || !modal || !iframe) return;
      // Append autoplay params if missing
      const sep = url.includes('?') ? '&' : '?';
      iframe.src = url + sep + 'autoplay=1';
      if (typeof modal.showModal === 'function') {
        modal.showModal(); 
      } else {
        modal.setAttribute('open','');
      }
    });
  });

  // Close resets src (stop playback)
  if (modal){
    modal.addEventListener('close', ()=>{ 
      iframe.src=''; 
    });
    
    modal.addEventListener('click', (e)=>{ 
      // click outside content closes
      const rect = modal.getBoundingClientRect();
      if (e.clientX < rect.left || e.clientX > rect.right || 
          e.clientY < rect.top || e.clientY > rect.bottom){
        modal.close();
      }
    });
  }
})();