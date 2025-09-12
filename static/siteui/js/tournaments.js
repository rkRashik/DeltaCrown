(function () {
  const $ = (s, c=document) => c.querySelector(s);
  const $$ = (s, c=document) => Array.from(c.querySelectorAll(s));

  // Copy link on detail
  const copy = $('#btn-copy');
  if (copy) {
    copy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(location.href); copy.textContent = 'Link copied!'; setTimeout(()=>copy.textContent='Copy link', 1800); } catch {}
    });
  }

  // Highlight active subnav as you scroll
  const sub = $('#subnav');
  const links = $$('#subnav .sub-link');
  const secs = ['overview','schedule','prizes','rules','registrations','bracket'].map(id => $('#'+id)).filter(Boolean);
  function onScroll() {
    if (!secs.length) return;
    let active = secs[0].id;
    const fromTop = window.scrollY + (sub ? sub.offsetHeight + 24 : 24);
    for (const s of secs) {
      if (s.offsetTop <= fromTop) active = s.id;
    }
    links.forEach(a => a.classList.toggle('bg-white/10', a.getAttribute('href') === '#'+active));
  }
  onScroll(); window.addEventListener('scroll', onScroll, { passive:true });
})();
