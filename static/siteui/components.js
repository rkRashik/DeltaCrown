(function(){
  var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Modal
  function openModal(id){
    var m = document.getElementById(id);
    if(!m) return;
    m.removeAttribute('hidden');
    m.setAttribute('aria-hidden','false');
    if(!prefersReduced){ m.querySelector('[data-modal-panel]')?.classList.remove('opacity-0','translate-y-4'); }
    // focus first focusable
    var first = m.querySelector('[data-autofocus]') || m.querySelector('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])');
    if(first){ first.focus(); }
  }
  function closeModal(id){
    var m = document.getElementById(id);
    if(!m) return;
    if(!prefersReduced){ m.querySelector('[data-modal-panel]')?.classList.add('opacity-0','translate-y-4'); }
    m.setAttribute('aria-hidden','true');
    m.setAttribute('hidden','');
  }
  document.addEventListener('click', function(e){
    var t = e.target;
    if(t.matches('[data-open-modal]')){
      e.preventDefault();
      openModal(t.getAttribute('data-open-modal'));
    } else if(t.matches('[data-close-modal]')){
      e.preventDefault();
      closeModal(t.getAttribute('data-close-modal'));
    } else if(t.matches('[data-modal-overlay]')){
      // click outside panel closes
      var id = t.closest('[role="dialog"]')?.id;
      if(id){ closeModal(id); }
    }
  });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape'){
      document.querySelectorAll('[role="dialog"]:not([hidden])').forEach(function(m){ closeModal(m.id); });
      document.querySelectorAll('[data-drawer]:not([hidden])').forEach(function(d){ toggleDrawer(d.id, false); });
    }
  });

  // Drawer
  function toggleDrawer(id, open){
    var d = document.getElementById(id);
    if(!d) return;
    var isOpen = !d.hasAttribute('hidden');
    var willOpen = (typeof open === 'boolean') ? open : !isOpen;
    if(willOpen){
      d.removeAttribute('hidden');
      d.setAttribute('aria-hidden','false');
      if(!prefersReduced){ d.querySelector('[data-drawer-panel]')?.classList.remove('-translate-x-full'); }
      d.querySelector('[data-autofocus]')?.focus();
    } else {
      if(!prefersReduced){ d.querySelector('[data-drawer-panel]')?.classList.add('-translate-x-full'); }
